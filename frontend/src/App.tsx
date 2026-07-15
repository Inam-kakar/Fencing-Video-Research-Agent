import { useState } from "react";

import { AppNavigation, type AppView } from "./components/AppNavigation";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { RunsPage } from "./pages/RunsPage";
import { SearchHitsPage } from "./pages/SearchHitsPage";
import { VideosPage } from "./pages/VideosPage";

export default function App() {
  const [currentView, setCurrentView] = useState<AppView>("dashboard");

  return (
    <Layout
      navigation={<AppNavigation currentView={currentView} onViewChange={setCurrentView} />}
    >
      {currentView === "dashboard" ? <DashboardPage /> : null}
      {currentView === "videos" ? <VideosPage /> : null}
      {currentView === "runs" ? <RunsPage /> : null}
      {currentView === "search-hits" ? <SearchHitsPage /> : null}
    </Layout>
  );
}
