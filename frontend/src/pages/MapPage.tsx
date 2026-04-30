import { OperationsMap } from "../maps/OperationsMap";
import { useOperationsData } from "../hooks/useOperationsData";

export function MapPage() {
  const data = useOperationsData();
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-white">Operational Map</h1>
        <p className="mt-1 text-sm text-slate-400">Layered sargassum, vessel, client, route, and collection-zone intelligence.</p>
      </div>
      <OperationsMap {...data} />
    </div>
  );
}
