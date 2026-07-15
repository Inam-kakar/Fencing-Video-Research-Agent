import { Card, CardContent, Stack, Typography } from "@mui/material";

type SummaryCardProps = {
  label: string;
  value: number;
  detail: string;
};

export function SummaryCard({ label, value, detail }: SummaryCardProps) {
  return (
    <Card sx={{ minWidth: { xs: "100%", sm: 220 }, flex: "1 1 220px" }}>
      <CardContent>
        <Stack spacing={1}>
          <Typography color="text.secondary" variant="body2">
            {label}
          </Typography>
          <Typography component="p" variant="h1">
            {value.toLocaleString()}
          </Typography>
          <Typography color="text.secondary" variant="body2">
            {detail}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}
