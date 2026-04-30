import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import type {
  Alert,
  ClientSite,
  CollectionZone,
  Observation,
  Patch,
  RouteRecommendation,
  Summary,
  Task,
  Vessel,
  VesselPosition
} from "../types/api";

export interface OperationsData {
  summary?: Summary;
  observations: Observation[];
  patches: Patch[];
  sites: ClientSite[];
  vessels: Vessel[];
  positions: VesselPosition[];
  zones: CollectionZone[];
  tasks: Task[];
  alerts: Alert[];
  routes: RouteRecommendation[];
  loading: boolean;
  error?: string;
  refresh: () => Promise<void>;
}

export function useOperationsData(): OperationsData {
  const [summary, setSummary] = useState<Summary>();
  const [observations, setObservations] = useState<Observation[]>([]);
  const [patches, setPatches] = useState<Patch[]>([]);
  const [sites, setSites] = useState<ClientSite[]>([]);
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [positions, setPositions] = useState<VesselPosition[]>([]);
  const [zones, setZones] = useState<CollectionZone[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [routes, setRoutes] = useState<RouteRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const refresh = async () => {
    setLoading(true);
    setError(undefined);
    try {
      const [summaryData, observationsData, patchesData, sitesData, vesselsData, positionsData, zonesData, tasksData, alertsData, routesData] =
        await Promise.all([
          api.summary(),
          api.observations(),
          api.patches(),
          api.clientSites(),
          api.vessels(),
          api.vesselPositions(),
          api.collectionZones(),
          api.tasks(),
          api.alerts(),
          api.routes()
        ]);
      setSummary(summaryData);
      setObservations(observationsData);
      setPatches(patchesData);
      setSites(sitesData);
      setVessels(vesselsData);
      setPositions(positionsData);
      setZones(zonesData);
      setTasks(tasksData);
      setAlerts(alertsData);
      setRoutes(routesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load operations data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 30000);
    return () => window.clearInterval(timer);
  }, []);

  return useMemo(
    () => ({ summary, observations, patches, sites, vessels, positions, zones, tasks, alerts, routes, loading, error, refresh }),
    [summary, observations, patches, sites, vessels, positions, zones, tasks, alerts, routes, loading, error]
  );
}
