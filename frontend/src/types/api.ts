export type Severity = "low" | "medium" | "high" | "critical";

export interface Summary {
  observations: number;
  patches: number;
  critical_patches: number;
  vessels: number;
  active_tasks: number;
  unread_alerts: number;
}


export interface Observation {
  id: number;
  latitude: number;
  longitude: number;
  observed_at?: string;
  source_type: string;
  source_reference?: string;
  density_level: string;
  estimated_area_m2?: number;
  confidence_score: number;
  notes?: string;
}

export interface Patch {
  id: number;
  patch_reference: string;
  severity: Severity;
  centroid_latitude: number;
  centroid_longitude: number;
  estimated_area_m2: number;
  density_level: string;
  movement_direction_degrees: number;
  movement_speed_knots: number;
  confidence_score: number;
  source_type: string;
  notes?: string;
}

export interface ClientSite {
  id: number;
  site_name: string;
  site_type: string;
  priority_level: number;
  latitude: number;
  longitude: number;
  current_risk: string;
  notes?: string;
}

export interface Vessel {
  id: number;
  vessel_name: string;
  vessel_type: string;
  operator: string;
  home_port: string;
  fuel_cost_per_hour: number;
  operating_cost_per_hour: number;
  max_speed_knots: number;
  working_speed_knots: number;
  collection_capacity_kg: number;
  gps_enabled: boolean;
  status: string;
}

export interface VesselPosition {
  id: number;
  vessel_id: number;
  latitude: number;
  longitude: number;
  heading: number;
  speed: number;
  timestamp: string;
  source_type: string;
}

export interface CollectionZone {
  id: number;
  zone_name: string;
  center_latitude: number;
  center_longitude: number;
  severity: Severity;
  estimated_volume_kg: number;
  priority_score: number;
  confidence_score: number;
  notes?: string;
}

export interface Task {
  id: number;
  task_reference: string;
  collection_zone_id: number;
  assigned_vessel_id?: number;
  priority: string;
  status: string;
  estimated_volume_kg: number;
  estimated_cost: number;
  estimated_duration: number;
  recommended_start_time?: string;
  created_at: string;
}

export interface Alert {
  id: number;
  alert_type: string;
  severity: Severity;
  message: string;
  related_object_type?: string;
  related_object_id?: number;
  recommended_action?: string;
  is_read: boolean;
  created_at: string;
}

export interface RouteRecommendation {
  vessel_id: number;
  vessel_name: string;
  collection_zone_id: number;
  zone_name: string;
  distance_nm: number;
  estimated_travel_hours: number;
  estimated_cost: number;
  estimated_collection_quantity_kg: number;
  estimated_time_to_complete: number;
  recommendation_score: number;
  action: string;
  reasoning_summary: string;
}


export interface PredictionPoint {
  hour: number;
  latitude: number;
  longitude: number;
}

export interface PredictionTrack {
  patch_id: number;
  patch_reference: string;
  severity: Severity;
  start: { latitude: number; longitude: number };
  future_positions: PredictionPoint[];
  drift_polygon: { type: string; coordinates: number[][][] };
  possible_impacts: Array<{ zone_name: string; distance_nm: number; estimated_arrival_hours: number; risk: string }>;
  confidence_score: number;
  environment: {
    source: string;
    ocean_current_direction_degrees?: number;
    ocean_current_speed_knots?: number;
    error?: string;
  };
}

export interface PredictionTrackResponse {
  horizon_hours: number;
  tracks: PredictionTrack[];
}


export type BandGrid = number[][];
export type MaskGrid = boolean[][];

export interface SpectralDetectionPayload {
  source_reference?: string;
  red_band: BandGrid;
  nir_band: BandGrid;
  swir_band: BandGrid;
  cloud_mask?: MaskGrid;
  land_mask?: MaskGrid;
  sun_glint_mask?: MaskGrid;
}

export interface GeoJsonFeature {
  type: "Feature";
  geometry: { type: string; coordinates: unknown };
  properties: Record<string, unknown>;
}

export interface SpectralDetectionResponse {
  algorithm: string;
  summary: {
    detected_pixels: number;
    total_pixels: number;
    coverage_ratio: number;
    density_level: string;
    confidence_score: number;
    mean_ndvi: number;
    mean_fai: number;
    generated_polygons?: number;
  };
  features: GeoJsonFeature[];
  polygon_features: GeoJsonFeature[];
  masking?: {
    cloud_mask_applied: boolean;
    land_mask_applied: boolean;
    sun_glint_mask_applied: boolean;
    notes: string;
  };
}

export interface SpectralIngestResponse extends SpectralDetectionResponse {
  persisted: boolean;
  reason: string;
  created_observation_ids: number[];
  created_patch_ids: number[];
  created_collection_zone_ids: number[];
  created_prediction_run_ids: number[];
  created_drift_zone_ids: number[];
  created_observations: number;
  created_patches: number;
  created_collection_zones: number;
  generated_polygons: number;
  drift_predictions: Array<{
    patch_id: number;
    horizon_hours: number;
    future_positions: PredictionPoint[];
    drift_polygon: { type: string; coordinates: unknown };
    confidence_score: number;
  }>;
}
