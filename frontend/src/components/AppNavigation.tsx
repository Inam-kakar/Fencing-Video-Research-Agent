import { Box, Tabs, Tab } from "@mui/material";

export type AppView = "dashboard" | "videos" | "runs" | "search-hits";

type AppNavigationProps = {
  currentView: AppView;
  onViewChange: (view: AppView) => void;
};

const views: Array<{ value: AppView; label: string }> = [
  { value: "dashboard", label: "Dashboard" },
  { value: "videos", label: "Videos" },
  { value: "runs", label: "Collection Runs" },
  { value: "search-hits", label: "Search Hits" },
];

export function AppNavigation({ currentView, onViewChange }: AppNavigationProps) {
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
      <Tabs
        aria-label="Dashboard views"
        onChange={(_, value: AppView) => onViewChange(value)}
        value={currentView}
        variant="scrollable"
      >
        {views.map((view) => (
          <Tab key={view.value} label={view.label} value={view.value} />
        ))}
      </Tabs>
    </Box>
  );
}
