import { Stack, Typography } from "@mui/material";

type PageHeaderProps = {
  title: string;
  description: string;
};

export function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <Stack spacing={1}>
      <Typography component="h1" variant="h1">
        {title}
      </Typography>
      <Typography color="text.secondary" maxWidth="760px" variant="body1">
        {description}
      </Typography>
    </Stack>
  );
}
