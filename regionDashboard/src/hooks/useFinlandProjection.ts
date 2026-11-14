import rewind from "@mapbox/geojson-rewind";
import { geoMercator, type GeoProjection } from "d3-geo";
import type { FeatureCollection } from "geojson";
import { useEffect, useState } from "react";
import { FINLAND_COUNTIES_GEOJSON_URL } from "../data/geoJoin";

/** Tall canvas matching Finland’s aspect so fitExtent isn’t letterboxed oddly. */
const WIDTH = 400;
const HEIGHT = 780;
const PAD = 18;

/**
 * Mercator projection fitted to the bundled wellbeing-county GeoJSON.
 * StatFi rings are clockwise; we rewind to RFC7946 so d3 doesn't treat them as
 * holes in the world (which paints a solid rectangle).
 */
export function useFinlandProjection(): {
  projection: GeoProjection | null;
  geography: FeatureCollection | null;
  error: string | null;
} {
  const [projection, setProjection] = useState<GeoProjection | null>(null);
  const [geography, setGeography] = useState<FeatureCollection | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(FINLAND_COUNTIES_GEOJSON_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load map (${res.status})`);
        return res.json() as Promise<FeatureCollection>;
      })
      .then((fc) => {
        if (cancelled) return;
        const fixed = rewind(fc, true) as FeatureCollection;
        const proj = geoMercator().fitExtent(
          [
            [PAD, PAD],
            [WIDTH - PAD, HEIGHT - PAD],
          ],
          fixed,
        );
        proj.clipExtent(null);
        setGeography(fixed);
        setProjection(() => proj);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Map load failed");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { projection, geography, error };
}

export const FINLAND_MAP_SIZE = { width: WIDTH, height: HEIGHT };
