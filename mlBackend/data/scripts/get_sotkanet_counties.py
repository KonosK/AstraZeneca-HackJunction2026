import time
import requests
import pandas as pd

BASE_URL = "https://sotkanet.fi/rest/1.1"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
})

def fetch_json(url: str, params=None):
    resp = session.get(url, params=params, timeout=30)
    resp.raise_for_status()
    if not resp.text.strip():
        raise ValueError(f"Empty response from {resp.url} (status {resp.status_code})")
    return resp.json()

# 1. Fetch all 21 Wellbeing Services Counties (Hyvinvointialueet)
regions = fetch_json(f"{BASE_URL}/regions")
counties = {
    r["id"]: r["title"]["en"]
    for r in regions
    if r.get("category") == "HYVINVOINTIALUE"
}
print(f"✅ Loaded {len(counties)} Wellbeing Services Counties.")

# 2. Verified real Sotkanet indicator IDs
CORE_INDICATORS = {
    6411: "gp_wait_over_7d_pct",          # Primary care elective doctor wait >7 days (%)
    3175: "gp_wait_over_3mo_pct",         # Primary care non-emergency doctor wait >3 months (%)
    4137: "gp_outpatient_visits_per_1000",# Primary care outpatient visits per 1,000
    5641: "morbidity_index_age_std",      # Age-standardised morbidity index
    3195: "higher_education_pct",         # Higher education qualifications, age 20+ (%)
    237:  "pop_75plus_living_alone_pct",  # Population aged 75+ living alone (%)
    5517: "pop_75plus_rai_assessed_pct",  # Elderly 75+ assessed with RAI functional tool (%)
}

# 3. Auto-discover official Cancer Registry cancer & screening indicators in Sotkanet
all_indicators = fetch_json(f"{BASE_URL}/indicators")
cancer_indicators = {}

for ind in all_indicators:
    title_en = ind.get("title", {}).get("en", "")
    title_lower = title_en.lower()
    # Grab key cancer incidence/mortality/screening metrics
    if ("cancer" in title_lower or "screening" in title_lower) and any(
        k in title_lower for k in ["incidence", "mortality", "trachea, bronchus and lung", "breast cancer screening", "cervical cancer screening"]
    ):
        clean_name = (
            title_en.lower()
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "_")
            .replace(" ", "_")[:45]
        )
        cancer_indicators[ind["id"]] = f"cr_{ind['id']}_{clean_name}"

print(f"🔎 Discovered {len(cancer_indicators)} Cancer Registry indicators in Sotkanet:")
for k, v in list(cancer_indicators.items())[:8]:
    print(f"   • ID {k}: {v}")

# Combine core indicators + up to 6 discovered cancer/screening indicators
SELECTED_INDICATORS = {**CORE_INDICATORS, **dict(list(cancer_indicators.items())[:6])}

# 4. Pull multi-year data across all counties
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
frames = []

for ind_id, col_name in SELECTED_INDICATORS.items():
    try:
        params = [("indicator", ind_id), ("genders", "total")] + [("years", y) for y in YEARS]
        rows = fetch_json(f"{BASE_URL}/json", params=params)
        records = [
            {
                "region_id": r["region"],
                "region_name": counties[r["region"]],
                "year": r["year"],
                col_name: r["value"],
            }
            for r in rows
            if r.get("region") in counties
        ]
        if records:
            df_ind = pd.DataFrame(records)
            frames.append(df_ind)
            print(f"   ✓ Pulled {len(df_ind):>3} rows -> {col_name}")
        time.sleep(0.2)
    except Exception as e:
        print(f"   ✗ Skipped ID {ind_id} ({col_name}): {e}")

# 5. Merge into final training table
df_final = frames[0]
for f in frames[1:]:
    df_final = pd.merge(df_final, f, on=["region_id", "region_name", "year"], how="outer")

df_final = df_final.sort_values(["region_name", "year"]).reset_index(drop=True)
df_final.to_csv("final_real_cancer_dataset.csv", index=False)

print(f"\n🎉 Saved {df_final.shape[0]} rows × {df_final.shape[1]} columns to final_real_cancer_dataset.csv")
print("\nMissing values per column:")
print(df_final.isna().sum())