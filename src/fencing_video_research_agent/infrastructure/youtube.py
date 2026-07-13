"""Official YouTube Data API adapter for the YouTube gateway port."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from importlib import import_module
from typing import Protocol, cast

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import SecretStr

from fencing_video_research_agent.domain import SearchParameterValue, YouTubeMetadata
from fencing_video_research_agent.ports import (
    Clock,
    PermanentYouTubeGatewayError,
    TransientYouTubeGatewayError,
    YouTubeSearchRequest,
    YouTubeSearchResult,
)

from .settings import ConfigurationError

SEARCH_PART = "snippet"
VIDEO_PARTS = "snippet,contentDetails,statistics"
MAX_SEARCH_PAGE_SIZE = 50
MAX_VIDEO_BATCH_SIZE = 50

SUPPORTED_SEARCH_PARAMETERS = frozenset(
    {
        "order",
        "publishedAfter",
        "publishedBefore",
        "regionCode",
        "relevanceLanguage",
        "safeSearch",
        "videoDuration",
        "videoEmbeddable",
        "videoSyndicated",
        "channelId",
    }
)
RESERVED_SEARCH_PARAMETERS = frozenset({"part", "q", "type", "maxResults", "pageToken"})
QUOTA_ERROR_REASONS = frozenset(
    {
        "dailyLimitExceeded",
        "dailyLimitExceededUnreg",
        "quotaExceeded",
        "userRateLimitExceeded",
    }
)
TRANSIENT_ERROR_REASONS = frozenset(
    {
        "backendError",
        "internalError",
        "rateLimitExceeded",
    }
)


class YouTubeDataApiExecutable(Protocol):
    """Executable Google API request."""

    def execute(self) -> Mapping[str, object]:
        """Execute the API request and return a response mapping."""


class YouTubeDataApiResource(Protocol):
    """Google API resource supporting list requests."""

    def list(self, **kwargs: object) -> YouTubeDataApiExecutable:
        """Create a list request."""


class YouTubeDataApiClient(Protocol):
    """Small protocol for the YouTube Data API client used by this adapter."""

    def search(self) -> YouTubeDataApiResource:
        """Return the search resource."""

    def videos(self) -> YouTubeDataApiResource:
        """Return the videos resource."""


type Sleep = Callable[[float], None]


def create_youtube_data_api_client(api_key: SecretStr | str) -> YouTubeDataApiClient:
    """Create an official YouTube Data API v3 client."""

    secret_value = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
    if not secret_value.strip():
        msg = "Missing or invalid configuration: YOUTUBE_API_KEY is required"
        raise ConfigurationError(msg)

    return cast(
        YouTubeDataApiClient,
        build(
            "youtube",
            "v3",
            developerKey=secret_value,
            cache_discovery=False,
        ),
    )


class YouTubeDataApiGateway:
    """YouTubeGateway implementation backed by the official YouTube Data API."""

    def __init__(
        self,
        *,
        client: YouTubeDataApiClient,
        clock: Clock,
        max_retries: int = 2,
        retry_sleep_seconds: float = 1.0,
        sleep: Sleep = time.sleep,
    ) -> None:
        if max_retries < 0:
            msg = "max_retries must be non-negative"
            raise ValueError(msg)
        if retry_sleep_seconds < 0:
            msg = "retry_sleep_seconds must be non-negative"
            raise ValueError(msg)

        self._client: YouTubeDataApiClient = client
        self._clock: Clock = clock
        self._max_retries: int = max_retries
        self._retry_sleep_seconds: float = retry_sleep_seconds
        self._sleep: Sleep = sleep

    def search_videos(self, request: YouTubeSearchRequest) -> tuple[YouTubeSearchResult, ...]:
        """Search for public YouTube videos using search.list."""

        search_parameters = _validated_search_parameters(request.parameters)
        results: list[YouTubeSearchResult] = []
        page_token: str | None = None
        next_rank = 1

        while len(results) < request.max_results:
            remaining_results = request.max_results - len(results)
            call_parameters: dict[str, object] = {
                "part": SEARCH_PART,
                "q": request.query_text,
                "type": "video",
                "maxResults": min(MAX_SEARCH_PAGE_SIZE, remaining_results),
                **search_parameters,
            }
            if page_token is not None:
                call_parameters["pageToken"] = page_token

            response = self._execute(self._client.search().list(**call_parameters))
            items = _response_items(response)

            for item in items:
                if len(results) >= request.max_results:
                    break
                results.append(_search_result_from_item(item, rank=next_rank))
                next_rank += 1

            page_token = _optional_string(response, "nextPageToken", "search.nextPageToken")
            if page_token is None:
                break

        return tuple(results)

    def fetch_video_metadata(self, video_ids: Sequence[str]) -> tuple[YouTubeMetadata, ...]:
        """Fetch latest YouTube metadata using videos.list."""

        unique_video_ids = _deduplicate_video_ids(video_ids)
        if not unique_video_ids:
            return ()

        last_refreshed_at = self._clock.utcnow()
        metadata: list[YouTubeMetadata] = []
        for batch in _chunks(unique_video_ids, MAX_VIDEO_BATCH_SIZE):
            response = self._execute(
                self._client.videos().list(
                    part=VIDEO_PARTS,
                    id=",".join(batch),
                )
            )
            metadata.extend(
                _metadata_from_item(item, last_refreshed_at=last_refreshed_at)
                for item in _response_items(response)
            )

        return tuple(metadata)

    def _execute(self, request: YouTubeDataApiExecutable) -> Mapping[str, object]:
        attempts = 0
        while True:
            try:
                response = request.execute()
            except HttpError as exc:
                classification = _classify_http_error(exc)
                if classification == "quota":
                    raise PermanentYouTubeGatewayError(
                        _sanitized_http_error_message("YouTube API quota exhausted", exc)
                    ) from exc
                if classification == "transient":
                    if attempts < self._max_retries:
                        self._sleep(self._retry_delay(attempts))
                        attempts += 1
                        continue
                    raise TransientYouTubeGatewayError(
                        _sanitized_http_error_message(
                            "Transient YouTube API failure after retries",
                            exc,
                        )
                    ) from exc
                raise PermanentYouTubeGatewayError(
                    _sanitized_http_error_message("Permanent YouTube API failure", exc)
                ) from exc
            except (ConnectionError, OSError, TimeoutError) as exc:
                if attempts < self._max_retries:
                    self._sleep(self._retry_delay(attempts))
                    attempts += 1
                    continue
                msg = f"Transient YouTube API transport failure after retries: {type(exc).__name__}"
                raise TransientYouTubeGatewayError(msg) from exc

            if not isinstance(response, Mapping):
                msg = "YouTube API response was not a mapping"
                raise PermanentYouTubeGatewayError(msg)
            return response

    def _retry_delay(self, attempt: int) -> float:
        return float(self._retry_sleep_seconds) * float(2**attempt)


def _validated_search_parameters(
    parameters: Mapping[str, SearchParameterValue],
) -> dict[str, object]:
    validated: dict[str, object] = {}
    for key, value in parameters.items():
        if key in RESERVED_SEARCH_PARAMETERS:
            msg = f"Search parameter cannot override adapter-controlled field: {key}"
            raise PermanentYouTubeGatewayError(msg)
        if key not in SUPPORTED_SEARCH_PARAMETERS:
            msg = f"Unsupported YouTube search parameter: {key}"
            raise PermanentYouTubeGatewayError(msg)
        if value is not None:
            validated[key] = value
    return validated


def _deduplicate_video_ids(video_ids: Sequence[str]) -> tuple[str, ...]:
    seen_video_ids: set[str] = set()
    unique_video_ids: list[str] = []
    for video_id in video_ids:
        normalized_video_id = video_id.strip()
        if not normalized_video_id:
            msg = "YouTube video ID must not be empty"
            raise PermanentYouTubeGatewayError(msg)
        if normalized_video_id in seen_video_ids:
            continue
        seen_video_ids.add(normalized_video_id)
        unique_video_ids.append(normalized_video_id)
    return tuple(unique_video_ids)


def _chunks(values: Sequence[str], size: int) -> Iterable[tuple[str, ...]]:
    for start_index in range(0, len(values), size):
        yield tuple(values[start_index : start_index + size])


def _response_items(response: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    value = response.get("items", ())
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        msg = "YouTube API response items must be a sequence"
        raise PermanentYouTubeGatewayError(msg)

    items: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            msg = "YouTube API response item must be a mapping"
            raise PermanentYouTubeGatewayError(msg)
        items.append(cast(Mapping[str, object], item))
    return tuple(items)


def _search_result_from_item(
    item: Mapping[str, object],
    *,
    rank: int,
) -> YouTubeSearchResult:
    identifier = _required_mapping(item, "id", "search.id")
    snippet = _optional_mapping(item, "snippet", "search.snippet")

    return YouTubeSearchResult(
        youtube_video_id=_required_string(identifier, "videoId", "search.id.videoId"),
        rank=rank,
        title=_optional_string(snippet, "title", "search.snippet.title") if snippet else None,
        channel_id=_optional_string(snippet, "channelId", "search.snippet.channelId")
        if snippet
        else None,
        channel_title=_optional_string(
            snippet,
            "channelTitle",
            "search.snippet.channelTitle",
        )
        if snippet
        else None,
        published_at=_parse_optional_datetime(
            _optional_string(snippet, "publishedAt", "search.snippet.publishedAt")
            if snippet
            else None,
            "search.snippet.publishedAt",
        ),
    )


def _metadata_from_item(
    item: Mapping[str, object],
    *,
    last_refreshed_at: datetime,
) -> YouTubeMetadata:
    video_id = _required_string(item, "id", "video.id")
    snippet = _required_mapping(item, "snippet", "video.snippet")
    content_details = _optional_mapping(item, "contentDetails", "video.contentDetails")
    statistics = _optional_mapping(item, "statistics", "video.statistics")

    return YouTubeMetadata(
        youtube_video_id=video_id,
        title=_required_string(snippet, "title", "video.snippet.title"),
        description=_optional_string(snippet, "description", "video.snippet.description"),
        channel_id=_required_string(snippet, "channelId", "video.snippet.channelId"),
        channel_title=_required_string(
            snippet,
            "channelTitle",
            "video.snippet.channelTitle",
        ),
        published_at=_parse_optional_datetime(
            _optional_string(snippet, "publishedAt", "video.snippet.publishedAt"),
            "video.snippet.publishedAt",
        ),
        duration=_parse_optional_duration(
            _optional_string(content_details, "duration", "video.contentDetails.duration")
            if content_details
            else None,
            "video.contentDetails.duration",
        ),
        view_count=_optional_integer(statistics, "viewCount", "video.statistics.viewCount")
        if statistics
        else None,
        like_count=_optional_integer(statistics, "likeCount", "video.statistics.likeCount")
        if statistics
        else None,
        comment_count=_optional_integer(
            statistics,
            "commentCount",
            "video.statistics.commentCount",
        )
        if statistics
        else None,
        last_refreshed_at=last_refreshed_at,
        tags=_optional_tags(snippet, "tags", "video.snippet.tags"),
        thumbnail_url=_thumbnail_url(snippet),
        video_url=f"https://www.youtube.com/watch?v={video_id}",
    )


def _required_mapping(
    container: Mapping[str, object],
    key: str,
    path: str,
) -> Mapping[str, object]:
    value = container.get(key)
    if not isinstance(value, Mapping):
        msg = f"Missing or invalid required YouTube field: {path}"
        raise PermanentYouTubeGatewayError(msg)
    return cast(Mapping[str, object], value)


def _optional_mapping(
    container: Mapping[str, object],
    key: str,
    path: str,
) -> Mapping[str, object] | None:
    value = container.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        msg = f"Invalid optional YouTube field: {path}"
        raise PermanentYouTubeGatewayError(msg)
    return cast(Mapping[str, object], value)


def _required_string(container: Mapping[str, object], key: str, path: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"Missing or invalid required YouTube field: {path}"
        raise PermanentYouTubeGatewayError(msg)
    return value.strip()


def _optional_string(container: Mapping[str, object], key: str, path: str) -> str | None:
    value = container.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        msg = f"Invalid optional YouTube field: {path}"
        raise PermanentYouTubeGatewayError(msg)
    stripped = value.strip()
    return stripped or None


def _optional_integer(container: Mapping[str, object], key: str, path: str) -> int | None:
    value = container.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        if not value.strip():
            return None
        try:
            parsed_value = int(value)
        except ValueError as exc:
            msg = f"Invalid numeric YouTube field: {path}"
            raise PermanentYouTubeGatewayError(msg) from exc
    elif isinstance(value, int):
        parsed_value = value
    else:
        msg = f"Invalid numeric YouTube field: {path}"
        raise PermanentYouTubeGatewayError(msg)

    if parsed_value < 0:
        msg = f"Invalid negative YouTube field: {path}"
        raise PermanentYouTubeGatewayError(msg)
    return parsed_value


def _parse_optional_datetime(value: str | None, path: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed_value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        msg = f"Invalid YouTube datetime field: {path}"
        raise PermanentYouTubeGatewayError(msg) from exc
    if parsed_value.tzinfo is None:
        msg = f"Invalid naive YouTube datetime field: {path}"
        raise PermanentYouTubeGatewayError(msg)
    return parsed_value.astimezone(UTC)


def _parse_optional_duration(value: str | None, path: str) -> timedelta | None:
    if value is None:
        return None
    try:
        parse_duration = cast(
            Callable[[str], object],
            import_module("isodate").__dict__["parse_duration"],
        )
        parsed_value = parse_duration(value)
    except Exception as exc:
        msg = f"Invalid YouTube duration field: {path}"
        raise PermanentYouTubeGatewayError(msg) from exc
    if not isinstance(parsed_value, timedelta):
        msg = f"Unsupported YouTube duration field: {path}"
        raise PermanentYouTubeGatewayError(msg)
    if parsed_value < timedelta(0):
        msg = f"Invalid negative YouTube duration field: {path}"
        raise PermanentYouTubeGatewayError(msg)
    return parsed_value


def _optional_tags(container: Mapping[str, object], key: str, path: str) -> tuple[str, ...]:
    value = container.get(key)
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        msg = f"Invalid optional YouTube field: {path}"
        raise PermanentYouTubeGatewayError(msg)

    tags: list[str] = []
    for tag in value:
        if not isinstance(tag, str):
            msg = f"Invalid optional YouTube field: {path}"
            raise PermanentYouTubeGatewayError(msg)
        stripped = tag.strip()
        if stripped:
            tags.append(stripped)
    return tuple(tags)


def _thumbnail_url(snippet: Mapping[str, object]) -> str | None:
    thumbnails = _optional_mapping(snippet, "thumbnails", "video.snippet.thumbnails")
    if thumbnails is None:
        return None

    for thumbnail_name in ("maxres", "standard", "high", "medium", "default"):
        thumbnail = _optional_mapping(
            thumbnails,
            thumbnail_name,
            f"video.snippet.thumbnails.{thumbnail_name}",
        )
        if thumbnail is None:
            continue
        url = _optional_string(
            thumbnail,
            "url",
            f"video.snippet.thumbnails.{thumbnail_name}.url",
        )
        if url is not None:
            return url
    return None


def _classify_http_error(error: HttpError) -> str:
    status = _http_error_status(error)
    reasons = set(_http_error_reasons(error))

    if reasons & QUOTA_ERROR_REASONS:
        return "quota"
    if status == 429 or (status is not None and 500 <= status <= 504):
        return "transient"
    if reasons & TRANSIENT_ERROR_REASONS:
        return "transient"
    return "permanent"


def _sanitized_http_error_message(prefix: str, error: HttpError) -> str:
    status = _http_error_status(error)
    reasons = _http_error_reasons(error)
    status_text = str(status) if status is not None else "unknown"
    reason_text = ",".join(reasons) if reasons else "unknown"
    return f"{prefix} (status={status_text}, reason={reason_text})"


def _http_error_status(error: HttpError) -> int | None:
    response = getattr(error, "resp", None)
    status = getattr(response, "status", None)
    if isinstance(status, int):
        return status
    if isinstance(status, str) and status.isdigit():
        return int(status)
    return None


def _http_error_reasons(error: HttpError) -> tuple[str, ...]:
    content = getattr(error, "content", b"")
    if isinstance(content, bytes):
        raw_content = content.decode("utf-8", errors="replace")
    elif isinstance(content, str):
        raw_content = content
    else:
        return ()

    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, Mapping):
        return ()

    error_payload = payload.get("error")
    if not isinstance(error_payload, Mapping):
        return ()

    reasons: list[str] = []
    errors = error_payload.get("errors")
    if isinstance(errors, Sequence) and not isinstance(errors, str | bytes):
        for item in errors:
            if not isinstance(item, Mapping):
                continue
            reason = item.get("reason")
            if isinstance(reason, str) and reason:
                reasons.append(reason)

    reason = error_payload.get("reason")
    if isinstance(reason, str) and reason:
        reasons.append(reason)

    return tuple(dict.fromkeys(reasons))
