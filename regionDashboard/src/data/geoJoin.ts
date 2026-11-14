/**
 * Join key between StatFi GeoJSON and OncoFlow GET /regions:
 *   GeoJSON feature.properties.name  ===  region.region_name
 *
 * Source: Statistics Finland WFS
 *   tilastointialueet:hyvinvointialue4500k_2024 (EPSG:4326)
 * Bundled at: public/finland-wellbeing-counties.geojson
 *
 * Note: StatFi exterior rings are clockwise; the loader rewinds to RFC7946
 * (counter-clockwise) so d3-geo / react-simple-maps render county fills correctly.
 */

export const FINLAND_COUNTIES_GEOJSON_URL = "/finland-wellbeing-counties.geojson";

export interface WellbeingCountyProperties {
  id?: number;
  hyvinvointialue?: string;
  vuosi?: number;
  nimi?: string;
  namn?: string;
  name: string;
}

export function geoName(props: Record<string, unknown> | WellbeingCountyProperties): string {
  const name = (props as WellbeingCountyProperties).name;
  return typeof name === "string" ? name : "";
}
