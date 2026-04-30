import L from "leaflet";
import { useMemo, useState } from "react";
import { CircleMarker, LayersControl, MapContainer, Marker, Polygon, Polyline, Popup, TileLayer } from "react-leaflet";
import type { ClientSite, CollectionZone, Observation, Patch, PredictionTrack, RouteRecommendation, Vessel, VesselPosition } from "../types/api";
import { StatusPill } from "../components/StatusPill";

const markerIcon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41]
});

const severityColor: Record<string, string> = {
  low: "#22c55e",
  medium: "#38bdf8",
  high: "#f59e0b",
  critical: "#fb7185"
};

export function OperationsMap({
  observations,
  patches,
  sites,
  zones,
  vessels,
  positions,
  routes,
  predictionTracks
}: {
  observations: Observation[];
  patches: Patch[];
  sites: ClientSite[];
  zones: CollectionZone[];
  vessels: Vessel[];
  positions: VesselPosition[];
  routes: RouteRecommendation[];
  predictionTracks: PredictionTrack[];
}) {
  const [selected, setSelected] = useState<string>("Operational layer ready");
  const vesselById = useMemo(() => new Map(vessels.map((v) => [v.id, v])), [vessels]);
  const latestPositionByVessel = useMemo(() => new Map(positions.map((p) => [p.vessel_id, p])), [positions]);
  const firstRoute = routes[0];
  const firstRoutePosition = firstRoute ? latestPositionByVessel.get(firstRoute.vessel_id) : undefined;
  const firstRouteZone = firstRoute ? zones.find((z) => z.id === firstRoute.collection_zone_id) : undefined;

  return (
    <div className="relative h-[540px] overflow-hidden rounded-lg border border-white/10 lg:h-[720px]">
      <MapContainer center={[13.45, -59.65]} zoom={8} scrollWheelZoom className="z-0">
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <LayersControl position="topright">

          <LayersControl.Overlay checked name="Live sightings">
            <>
              {observations.slice(0, 250).map((observation) => (
                <CircleMarker
                  key={observation.id}
                  center={[observation.latitude, observation.longitude]}
                  radius={6}
                  pathOptions={{ color: "#f8fafc", fillColor: "#22d3ee", fillOpacity: 0.75, weight: 1 }}
                  eventHandlers={{ click: () => setSelected(`${observation.source_type}: ${observation.notes || "Sargassum sighting"}`) }}
                >
                  <Popup>
                    <strong>Sargassum sighting</strong>
                    <br />
                    Source: {observation.source_type}
                    <br />
                    Confidence: {Math.round(observation.confidence_score * 100)}%
                    <br />
                    {observation.observed_at ? new Date(observation.observed_at).toLocaleDateString() : "Date unknown"}
                  </Popup>
                </CircleMarker>
              ))}
            </>
          </LayersControl.Overlay>
          <LayersControl.Overlay checked name="Sargassum patches">
            <>
              {patches.map((patch) => (
                <CircleMarker
                  key={patch.id}
                  center={[patch.centroid_latitude, patch.centroid_longitude]}
                  radius={patch.severity === "critical" ? 22 : patch.severity === "high" ? 17 : 13}
                  pathOptions={{
                    color: severityColor[patch.severity],
                    fillColor: severityColor[patch.severity],
                    fillOpacity: 0.35,
                    weight: 2
                  }}
                  eventHandlers={{ click: () => setSelected(`${patch.patch_reference}: ${patch.notes || "Patch selected"}`) }}
                >
                  <Popup>
                    <strong>{patch.patch_reference}</strong>
                    <br />
                    Severity: {patch.severity}
                    <br />
                    Confidence: {Math.round(patch.confidence_score * 100)}%
                  </Popup>
                </CircleMarker>
              ))}
            </>
          </LayersControl.Overlay>

          <LayersControl.Overlay checked name="Predicted drift tracks">
            <>
              {predictionTracks.map((track) => {
                const line = [track.start, ...track.future_positions].map((point) => [point.latitude, point.longitude] as [number, number]);
                const polygon = track.drift_polygon?.coordinates?.[0]?.map(([lon, lat]) => [lat, lon] as [number, number]) || [];
                const last = track.future_positions[track.future_positions.length - 1];
                return (
                  <div key={track.patch_id}>
                    {polygon.length ? (
                      <Polygon
                        positions={polygon}
                        pathOptions={{ color: severityColor[track.severity], fillColor: severityColor[track.severity], fillOpacity: 0.12, weight: 2 }}
                      />
                    ) : null}
                    <Polyline
                      positions={line}
                      pathOptions={{ color: severityColor[track.severity], weight: 5, opacity: 0.95 }}
                      eventHandlers={{ click: () => setSelected(`${track.patch_reference}: forecast ${track.environment.ocean_current_direction_degrees ?? "?"}° at ${track.environment.ocean_current_speed_knots ?? "?"} kt`) }}
                    />
                    {track.future_positions.map((point) => (
                      <CircleMarker
                        key={`${track.patch_id}-${point.hour}`}
                        center={[point.latitude, point.longitude]}
                        radius={point.hour === 72 ? 8 : 5}
                        pathOptions={{ color: severityColor[track.severity], fillColor: "#ffffff", fillOpacity: 0.9, weight: 2 }}
                      >
                        <Popup>
                          <strong>{track.patch_reference}</strong>
                          <br />
                          Forecast hour: {point.hour}
                          <br />
                          Confidence: {Math.round(track.confidence_score * 100)}%
                          <br />
                          Current: {track.environment.ocean_current_direction_degrees ?? "?"}° / {track.environment.ocean_current_speed_knots ?? "?"} kt
                        </Popup>
                      </CircleMarker>
                    ))}
                    {last ? (
                      <CircleMarker
                        center={[last.latitude, last.longitude]}
                        radius={11}
                        pathOptions={{ color: "#ffffff", fillColor: severityColor[track.severity], fillOpacity: 0.75, weight: 2 }}
                      />
                    ) : null}
                  </div>
                );
              })}
            </>
          </LayersControl.Overlay>
          <LayersControl.Overlay checked name="Collection zones">
            <>
              {zones.map((zone) => (
                <CircleMarker
                  key={zone.id}
                  center={[zone.center_latitude, zone.center_longitude]}
                  radius={15}
                  pathOptions={{ color: "#a3e635", fillColor: "#84cc16", fillOpacity: 0.25, dashArray: "5 5" }}
                  eventHandlers={{ click: () => setSelected(`${zone.zone_name}: ${zone.notes || "Collection zone"}`) }}
                >
                  <Popup>
                    <strong>{zone.zone_name}</strong>
                    <br />
                    Volume: {zone.estimated_volume_kg.toLocaleString()} kg
                    <br />
                    Priority: {zone.priority_score}
                  </Popup>
                </CircleMarker>
              ))}
            </>
          </LayersControl.Overlay>
          <LayersControl.Overlay checked name="Vessels">
            <>
              {positions.map((pos) => {
                const vessel = vesselById.get(pos.vessel_id);
                return (
                  <Marker key={pos.id} position={[pos.latitude, pos.longitude]} icon={markerIcon}>
                    <Popup>
                      <strong>{vessel?.vessel_name || "Vessel"}</strong>
                      <br />
                      Status: {vessel?.status}
                      <br />
                      Speed: {pos.speed} kt
                    </Popup>
                  </Marker>
                );
              })}
            </>
          </LayersControl.Overlay>
          <LayersControl.Overlay checked name="Client sites">
            <>
              {sites.map((site) => (
                <CircleMarker
                  key={site.id}
                  center={[site.latitude, site.longitude]}
                  radius={9}
                  pathOptions={{ color: "#e0f2fe", fillColor: "#38bdf8", fillOpacity: 0.8 }}
                  eventHandlers={{ click: () => setSelected(`${site.site_name}: ${site.current_risk} risk`) }}
                >
                  <Popup>
                    <strong>{site.site_name}</strong>
                    <br />
                    Risk: {site.current_risk}
                  </Popup>
                </CircleMarker>
              ))}
            </>
          </LayersControl.Overlay>
          <LayersControl.Overlay checked name="Top route">
            <>
              {firstRoute && firstRoutePosition && firstRouteZone ? (
                <Polyline
                  positions={[
                    [firstRoutePosition.latitude, firstRoutePosition.longitude],
                    [firstRouteZone.center_latitude, firstRouteZone.center_longitude]
                  ]}
                  pathOptions={{ color: "#38bdf8", weight: 4, dashArray: "8 8" }}
                />
              ) : null}
            </>
          </LayersControl.Overlay>
        </LayersControl>
      </MapContainer>
      <div className="absolute bottom-3 left-3 right-3 z-[450] rounded-lg border border-white/10 bg-ink/90 p-3 backdrop-blur md:left-auto md:w-96">
        <p className="text-xs uppercase tracking-wide text-slate-400">Selected intelligence</p>
        <p className="mt-1 text-sm text-slate-100">{selected}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <StatusPill value="critical" />
          <StatusPill value="high" />
          <StatusPill value="medium" />
        </div>
      </div>
    </div>
  );
}
