import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { OverviewPage } from "./pages/OverviewPage";
import { MapPage } from "./pages/MapPage";
import { SpectralDetectionPage } from "./pages/SpectralDetectionPage";
import { AdminPage, AlertsPage, ClientsPage, PredictionsPage, SettingsPage, TasksPage, VesselsPage } from "./pages/ListPages";

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/clients" element={<ClientsPage />} />
        <Route path="/vessels" element={<VesselsPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/predictions" element={<PredictionsPage />} />
        <Route path="/spectral" element={<SpectralDetectionPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
