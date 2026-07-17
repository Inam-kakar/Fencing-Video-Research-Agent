"""Application use case for collecting YouTube video metadata from a search query."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from fencing_video_research_agent.domain import (
    CollectionRun,
    SearchParameterValue,
    SearchQuery,
    Video,
    YouTubeMetadata,
)
from fencing_video_research_agent.ports import (
    Clock,
    CollectionRunRecordId,
    UnitOfWork,
    YouTubeGateway,
    YouTubeSearchRequest,
    YouTubeSearchResult,
)

type UnitOfWorkFactory = Callable[[], UnitOfWork]


@dataclass(frozen=True, slots=True)
class CollectVideosRequest:
    """Input for collecting videos from one YouTube search query."""

    query_text: str
    max_results: int
    parameters: Mapping[str, SearchParameterValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        query_text = self.query_text.strip()
        if not query_text:
            msg = "query_text must not be empty"
            raise ValueError(msg)
        if self.max_results < 1:
            msg = "max_results must be positive"
            raise ValueError(msg)
        object.__setattr__(self, "query_text", query_text)
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True, slots=True)
class CollectVideosResult:
    """Summary counts for one completed collection use case."""

    collection_run_id: CollectionRunRecordId
    query_text: str
    requested_max_results: int
    search_result_count: int
    unique_video_count: int
    stored_video_count: int
    search_hit_count: int
    duplicate_search_result_count: int


class MissingYouTubeMetadataError(Exception):
    """Raised when search returns videos that metadata enrichment does not return."""

    def __init__(self, missing_video_ids: Sequence[str]) -> None:
        self.missing_video_ids = tuple(missing_video_ids)
        joined_ids = ", ".join(self.missing_video_ids)
        super().__init__(f"missing YouTube metadata for video IDs: {joined_ids}")


@dataclass(frozen=True, slots=True)
class _SearchHitCandidate:
    youtube_video_id: str
    rank: int | None


class CollectVideosUseCase:
    """Collect and persist YouTube metadata for one search query."""

    def __init__(
        self,
        *,
        youtube_gateway: YouTubeGateway,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._youtube_gateway = youtube_gateway
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(self, request: CollectVideosRequest) -> CollectVideosResult:
        """Run discovery, metadata enrichment, and persistence for one query."""

        started_at = self._clock.utcnow()
        search_results = self._youtube_gateway.search_videos(
            YouTubeSearchRequest(
                query_text=request.query_text,
                max_results=request.max_results,
                parameters=request.parameters,
            )
        )
        search_hit_candidates = _deduplicate_search_results(search_results)
        metadata_by_id = self._fetch_metadata_by_id(search_hit_candidates)
        completed_at = self._clock.utcnow()

        search_query = SearchQuery(
            query_text=request.query_text,
            parameters=_stored_search_parameters(request),
        )
        collection_run = CollectionRun(
            search_query=search_query,
            started_at=started_at,
            completed_at=completed_at,
        )

        with self._unit_of_work_factory() as unit_of_work:
            collection_run_id = unit_of_work.collections.add_collection_run(
                collection_run,
                status="completed",
            )
            for candidate in search_hit_candidates:
                metadata = metadata_by_id[candidate.youtube_video_id]
                unit_of_work.videos.add_or_update(
                    Video(
                        youtube_video_id=candidate.youtube_video_id,
                        first_seen_at=started_at,
                        metadata=metadata,
                    )
                )
                unit_of_work.collections.add_search_hit(
                    collection_run_id,
                    youtube_video_id=candidate.youtube_video_id,
                    discovered_at=completed_at,
                    rank=candidate.rank,
                )
            unit_of_work.commit()

        return CollectVideosResult(
            collection_run_id=collection_run_id,
            query_text=request.query_text,
            requested_max_results=request.max_results,
            search_result_count=len(search_results),
            unique_video_count=len(search_hit_candidates),
            stored_video_count=len(search_hit_candidates),
            search_hit_count=len(search_hit_candidates),
            duplicate_search_result_count=len(search_results) - len(search_hit_candidates),
        )

    def _fetch_metadata_by_id(
        self,
        search_hit_candidates: tuple[_SearchHitCandidate, ...],
    ) -> dict[str, YouTubeMetadata]:
        if not search_hit_candidates:
            return {}

        video_ids = tuple(candidate.youtube_video_id for candidate in search_hit_candidates)
        metadata_by_id: dict[str, YouTubeMetadata] = {}
        for metadata in self._youtube_gateway.fetch_video_metadata(video_ids):
            metadata_by_id.setdefault(metadata.youtube_video_id, metadata)

        missing_video_ids = tuple(
            video_id for video_id in video_ids if video_id not in metadata_by_id
        )
        if missing_video_ids:
            raise MissingYouTubeMetadataError(missing_video_ids)

        return metadata_by_id


def _deduplicate_search_results(
    search_results: tuple[YouTubeSearchResult, ...],
) -> tuple[_SearchHitCandidate, ...]:
    seen_video_ids: set[str] = set()
    candidates: list[_SearchHitCandidate] = []
    for result in search_results:
        if result.youtube_video_id in seen_video_ids:
            continue
        seen_video_ids.add(result.youtube_video_id)
        candidates.append(
            _SearchHitCandidate(
                youtube_video_id=result.youtube_video_id,
                rank=result.rank,
            )
        )
    return tuple(candidates)


def _stored_search_parameters(
    request: CollectVideosRequest,
) -> Mapping[str, SearchParameterValue]:
    parameters = dict(request.parameters)
    parameters["max_results"] = request.max_results
    return MappingProxyType(parameters)
