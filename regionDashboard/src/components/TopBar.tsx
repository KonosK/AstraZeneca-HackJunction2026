import styles from "./TopBar.module.css";

export type SortMode = "name" | "metric_desc" | "metric_asc";

interface TopBarProps {
  search: string;
  onSearchChange: (v: string) => void;
  sort: SortMode;
  onSortChange: (s: SortMode) => void;
  year: number | null;
}

export function TopBar({
  search,
  onSearchChange,
  sort,
  onSortChange,
  year,
}: TopBarProps) {
  return (
    <header className={`panel ${styles.bar}`}>
      <div className={styles.titleBlock}>
        <h2 className={styles.title}>Counties</h2>
        <p className={styles.subtitle}>
          Search & sort
          {year != null ? ` · ${year}` : ""}
        </p>
      </div>

      <div className={styles.filters} role="group" aria-label="County list filters">
        <div className={styles.field}>
          <label htmlFor="county-search">Search</label>
          <input
            id="county-search"
            type="search"
            placeholder="e.g. Lapland"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            autoComplete="off"
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="county-sort">Sort</label>
          <select
            id="county-sort"
            value={sort}
            onChange={(e) => onSortChange(e.target.value as SortMode)}
          >
            <option value="name">Name A–Z</option>
            <option value="metric_desc">Metric high → low</option>
            <option value="metric_asc">Metric low → high</option>
          </select>
        </div>
      </div>
    </header>
  );
}
