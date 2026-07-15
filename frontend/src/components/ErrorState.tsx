import { Alert, Button, Stack } from "@mui/material";

type ErrorStateProps = {
  message: string;
  onRetry: () => void;
};

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <Stack spacing={2}>
      <Alert severity="error">{message}</Alert>
      <Button onClick={onRetry} variant="contained">
        Retry
      </Button>
    </Stack>
  );
}
