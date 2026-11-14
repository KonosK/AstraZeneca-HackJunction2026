import requests
import pandas as pd

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
})

df = pd.read_csv("../clean_cancer_training_data.csv")
county_ids = set(df["region_id"].unique())

params = [("indicator", 5643), ("genders", "total")] + [("years", y) for y in [2020, 2021, 2022, 2023, 2024]]
rows = session.get("https://sotkanet.fi/rest/1.1/json", params=params, timeout=30).json()

cancer_df = pd.DataFrame([
    {"region_id": r["region"], "year": r["year"], "cancer_index_age_std": r["value"]}
    for r in rows if r.get("region") in county_ids
])

df = pd.merge(df, cancer_df, on=["region_id", "year"], how="left")
df.to_csv("clean_cancer_training_data.csv", index=False)
print("✅ Added cancer_index_age_std! Missing values:", df["cancer_index_age_std"].isna().sum())
print(df[["region_name", "year", "gp_wait_over_7d_pct", "cancer_index_age_std"]].dropna().head(6).to_string(index=False))