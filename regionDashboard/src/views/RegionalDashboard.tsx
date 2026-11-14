import { useState } from "react";
import type { HealthResponse, OverlayMetric, RegionSummary } from "../api/types";
import { CountyInspector } from "../components/CountyInspector";
import { CountyList } from "../components/CountyList";
import { CountyMap } from "../components/CountyMap";
import { KpiStrip } from "../components/KpiStrip";
import { TopBar, type SortMode } from "../components/TopBar";

export interface RegionalDashboardProps {
  health: HealthResponse | null;
  regions: RegionSummary[];
  year: number | null;
  regionsLoading: boolean;
  regionsError: string | null;
  selected: RegionSummary | null;
  onSelect: (region: RegionSummary) => void;
}

/** OncoFlow regional dashboard shell (sidebar removed). */
export function RegionalDashboard({
  health,
  regions,
  year,
  regionsLoading,
  regionsError,
  selected,
  onSelect,
}: RegionalDashboardProps) {
  const [metric, setMetric] = useState<OverlayMetric>("observed_cancer_index");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortMode>("name");

  return (
    <div className="app-shell regional-dashboard no-sidebar">
      <div className="main-column">
        <div className="map-workspace">
          <CountyMap
            regions={regions}
            metric={metric}
            onMetricChange={setMetric}
            selectedId={selected?.region_id ?? null}
            onSelect={onSelect}
            search={search}
            loading={regionsLoading}
            error={regionsError}
          />
          <CountyInspector region={selected} />
        </div>

        <TopBar
          search={search}
          onSearchChange={setSearch}
          sort={sort}
          onSortChange={setSort}
          year={year}
        />

        <CountyList
          regions={regions}
          metric={metric}
          selectedId={selected?.region_id ?? null}
          onSelect={onSelect}
          search={search}
          sort={sort}
          loading={regionsLoading}
        />

        <KpiStrip regions={regions} health={health} loading={regionsLoading} />
      </div>
    </div>
  );
}
