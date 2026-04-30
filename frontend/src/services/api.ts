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

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(`API error ${response.status} for ${path}`);
  return response.json();
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) throw new Error(`API error ${response.status} for ${path}`);
  return response.json();
}

export const api = {
  seedDemo: () => postJson("/demo/seed"),
  ingestLiveObservations: () => postJson("/live/ingest-observations?days=180&limit=100"),
  liveSources: () => getJson("/live/sources"),
  summary: () => getJson<Summary>("/dashboard/summary"),
  observations: () => getJson<Observation[]>("/observations"),
  patches: () => getJson<Patch[]>("/patches"),
  clientSites: () => getJson<ClientSite[]>("/client-sites"),
  vessels: () => getJson<Vessel[]>("/vessels"),
  vesselPositions: () => getJson<VesselPosition[]>("/vessel-positions"),
  collectionZones: () => getJson<CollectionZone[]>("/collection-zones"),
  tasks: () => getJson<Task[]>("/tasks"),
  alerts: () => getJson<Alert[]>("/alerts"),
  routes: () => getJson<RouteRecommendation[]>("/routes/recommendations")
};
