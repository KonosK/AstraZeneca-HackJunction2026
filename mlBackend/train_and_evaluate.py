"""Train and evaluate cancer_index models with group-aware CV; save OncoFlow bundle."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline

_ROOT = Path(__file__).resolve().parent
DATA_PATH = _ROOT / "data" / "clean_cancer_training_data.csv"
ARTIFACT_PATH = _ROOT / "artifacts" / "oncoflow_bundle.joblib"

TARGET = "cancer_index_age_std"
GROUP_COL = "region_name"
FEATURES = [
    "gp_wait_over_7d_pct",
    "gp_wait_over_3mo_pct",
    "gp_outpatient_visits_per_1000",
    "higher_education_pct",
    "pop_75plus_living_alone_pct",
    "pop_75plus_rai_assessed_pct",
    "cr_3620_proportion_of_women_invited_to_cervical_cance",
    "cr_3621_proportion_of_women_invited_to_breast_cancer_",
]

TREE_MODELS = {"RandomForestRegressor", "GradientBoostingRegressor"}


def make_pipeline(estimator) -> Pipeline:
    """Median imputer inside the pipeline so fold medians never leak into test."""
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("model", estimator),
        ]
    )


def evaluate_model(
    name: str,
    estimator,
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    n_splits: int = 5,
) -> dict:
    cv = GroupKFold(n_splits=n_splits)
    maes, rmses, r2s = [], [], []

    for train_idx, test_idx in cv.split(X, y, groups):
        pipe = make_pipeline(estimator)
        pipe.fit(X.iloc[train_idx], y.iloc[train_idx])
        pred = pipe.predict(X.iloc[test_idx])
        y_true = y.iloc[test_idx]
        maes.append(mean_absolute_error(y_true, pred))
        rmses.append(mean_squared_error(y_true, pred) ** 0.5)
        r2s.append(r2_score(y_true, pred))

    return {
        "model": name,
        "mae_mean": float(np.mean(maes)),
        "mae_std": float(np.std(maes)),
        "rmse_mean": float(np.mean(rmses)),
        "rmse_std": float(np.std(rmses)),
        "r2_mean": float(np.mean(r2s)),
        "r2_std": float(np.std(r2s)),
        "mae_folds": [float(v) for v in maes],
        "rmse_folds": [float(v) for v in rmses],
        "r2_folds": [float(v) for v in r2s],
    }


def latest_county_table(
    df: pd.DataFrame, pipeline: Pipeline, features: list[str]
) -> pd.DataFrame:
    """One row per county: most recent year, with prediction."""
    latest = (
        df.sort_values("year")
        .groupby(GROUP_COL, as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )
    latest = latest.copy()
    latest["predicted_cancer_index_age_std"] = pipeline.predict(latest[features])
    keep = [
        "region_id",
        "region_name",
        "year",
        TARGET,
        "predicted_cancer_index_age_std",
        *features,
    ]
    return latest[keep]


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    df = df.dropna(subset=[TARGET]).copy()

    X = df[FEATURES]
    y = df[TARGET]
    groups = df[GROUP_COL]

    candidates = {
        "DummyRegressor": DummyRegressor(strategy="mean"),
        "Ridge": Ridge(alpha=1.0),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=200, random_state=42, n_jobs=-1
        ),
        "GradientBoostingRegressor": GradientBoostingRegressor(random_state=42),
    }

    cv_metrics = []
    for name, est in candidates.items():
        metrics = evaluate_model(name, est, X, y, groups)
        cv_metrics.append(metrics)
        print(
            f"{name:28s}  MAE={metrics['mae_mean']:.3f}±{metrics['mae_std']:.3f}  "
            f"RMSE={metrics['rmse_mean']:.3f}±{metrics['rmse_std']:.3f}  "
            f"R²={metrics['r2_mean']:.3f}±{metrics['r2_std']:.3f}"
        )

    # Prefer lowest MAE; TreeExplainer requires a tree model for the saved bundle.
    ranked = sorted(cv_metrics, key=lambda m: m["mae_mean"])
    best = next((m for m in ranked if m["model"] in TREE_MODELS), ranked[0])
    if best["model"] not in TREE_MODELS:
        raise RuntimeError(
            f"Best model {best['model']} is not tree-based; cannot build TreeExplainer."
        )
    if ranked[0]["model"] != best["model"]:
        print(
            f"Note: overall lowest MAE was {ranked[0]['model']}; "
            f"using {best['model']} for TreeExplainer bundle."
        )
    print(f"\nSelected best model: {best['model']} (MAE={best['mae_mean']:.3f})")

    final_pipeline = make_pipeline(candidates[best["model"]])
    final_pipeline.fit(X, y)

    # TreeExplainer needs the fitted tree estimator (imputer stays in the pipeline).
    tree_model = final_pipeline.named_steps["model"]
    explainer = shap.TreeExplainer(tree_model)

    county_table = latest_county_table(df, final_pipeline, FEATURES)

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "pipeline": final_pipeline,
        "explainer": explainer,
        "features": FEATURES,
        "latest_county_table": county_table,
        "cv_metrics": cv_metrics,
        "best_model": best["model"],
        "target": TARGET,
    }
    joblib.dump(bundle, ARTIFACT_PATH)
    print(f"Saved bundle -> {ARTIFACT_PATH.resolve()}")
    print(f"Latest county rows: {len(county_table)}")


if __name__ == "__main__":
    main()
