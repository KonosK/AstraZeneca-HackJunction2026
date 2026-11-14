import time
import requests
import pandas as pd

BASE_URL = "https://sotkanet.fi/rest/1.1"
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
})

df = pd.read_csv("final_real_cancer_dataset.csv")
county_ids = set(df["region_id"].unique())

# 1. Discover real Malignant Neoplasm (Cancer) mortality/incidence indicators
indicators = session.get(f"{BASE_URL}/indicators", timeout=30).json()
neoplasm_inds = {}

for ind in indicators:
    title = ind.get("title", {}).get("en", "")
    t_low = title.lower()
    if "malignant neoplasm" in t_low and any(k in t_low for k in ["mortality", "deaths", "inpatient", "per 100 000", "per 10 000"]):
        clean_col = "cancer_" + title.lower().replace(",", "").replace("(", "").replace(")", "").replace(" ", "_")[:42]
        neoplasm_inds[ind["id"]] = clean_col

print(f"🔎 Found {len(neoplasm_inds)} malignant neoplasm outcome indicators:")
for k, v in list(neoplasm_inds.items())[:6]:
    print(f"   • ID {k}: {v}")

# 2. Pull up to 4 neoplasm indicators across 2020-2024
YEARS = [2020, 2021, 2022, 2023, 2024]
for ind_id, col_name in list(neoplasm_inds.items())[:4]:
    params = [("indicator", ind_id), ("genders", "total")] + [("years", y) for y in YEARS]
    rows = session.get(f"{BASE_URL}/json", params=params, timeout=30).json()
    records = [
        {"region_id": r["region"], "year": r["year"], col_name: r["value"]}
        for r in rows
        if r.get("region") in county_ids
    ]
    if records:
        df = pd.merge(df, pd.DataFrame(records), on=["region_id", "year"], how="left")
        print(f"   ✓ Merged {len(records)} rows -> {col_name}")
    time.sleep(0.2)

# 3. Filter to 2020-2024 where reporting is complete and save
df_clean = df[df["year"].between(2020, 2024)].sort_values(["region_name", "year"]).reset_index(drop=True)
df_clean.to_csv("clean_cancer_training_data.csv", index=False)

print(f"\n🎉 Saved {df_clean.shape[0]} rows × {df_clean.shape[1]} columns to clean_cancer_training_data.csv")
print("\nMissing values in 2020-2024:")
print(df_clean.isna().sum())