import { Alert } from "@mui/material";

type DataTableEmptyStateProps = {
  message: string;
};

export function DataTableEmptyState({ message }: DataTableEmptyStateProps) {
  return <Alert severity="info">{message}</Alert>;
}
