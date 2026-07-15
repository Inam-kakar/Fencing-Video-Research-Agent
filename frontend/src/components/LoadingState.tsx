import { CircularProgress, Stack, Typography } from "@mui/material";

export function LoadingState() {
  return (
    <Stack alignItems="center" spacing={2} sx={{ py: 8 }}>
      <CircularProgress />
      <Typography color="text.secondary">Loading research dashboard data...</Typography>
    </Stack>
  );
}
