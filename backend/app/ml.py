from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score, log_loss,
    matthews_corrcoef, mean_absolute_error, mean_squared_error,
    median_absolute_error, precision_score, r2_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, OneHotEncoder, OrdinalEncoder, StandardScaler
from xgboost import XGBClassifier, XGBRegressor

from .utils.csv_security import protect_csv
from .utils.problem_type import suggest_problem

ID_PATTERN = re.compile(r"(^id$|_id$|^uuid$|uuid$)", re.I)


def json_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return None
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,)): return float(value)
    if isinstance(value, (pd.Timestamp, datetime)): return value.isoformat()
    return value


def detect_kind(series: pd.Series) -> str:
    clean = series.dropna()
    if not len(clean) or clean.nunique() <= 1: return "constant"
    if pd.api.types.is_bool_dtype(series): return "boolean"
    if pd.api.types.is_numeric_dtype(series): return "numeric"
    parsed = pd.to_datetime(clean.astype(str), errors="coerce", format="mixed")
    if len(clean) >= 3 and parsed.notna().mean() > .9: return "date"
    return "categorical"


def analyze(df: pd.DataFrame) -> tuple[list[dict], dict]:
    kinds = {c: detect_kind(df[c]) for c in df.columns}
    columns = []
    for name in df.columns:
        s, unique = df[name], int(df[name].nunique(dropna=True))
        columns.append({
            "name": str(name), "dtype": kinds[name], "unique": unique,
            "missing": int(s.isna().sum()), "missing_pct": round(float(s.isna().mean() * 100), 2),
            "examples": [str(json_value(x))[:80] for x in s.dropna().drop_duplicates().head(3)],
            "likely_id": bool(ID_PATTERN.search(str(name))) or (len(df) > 10 and unique / len(df) > .98),
            "problem_suggestion": suggest_problem(s),
        })
    summary = {
        "rows": len(df), "columns": len(df.columns), "missing_values": int(df.isna().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
    }
    for kind in ("numeric", "categorical", "date", "boolean", "constant"):
        summary[f"{kind}_columns"] = sum(v == kind for v in kinds.values())
    return columns, summary


def validate_training(df: pd.DataFrame, target: str, features: list[str], problem: str) -> list[str]:
    if target not in df: raise ValueError("The selected target column no longer exists.")
    missing = sorted(set(features) - set(df.columns))
    if missing: raise ValueError(f"Missing feature columns: {', '.join(missing)}")
    if target in features: raise ValueError("The target cannot also be a feature.")
    if not features: raise ValueError("Select at least one feature.")
    if df[target].dropna().nunique() < 2: raise ValueError("The target needs at least two distinct values.")
    if problem == "binary_classification" and df[target].dropna().nunique() != 2:
        raise ValueError("Binary classification requires exactly two target classes.")
    if problem == "regression" and not pd.api.types.is_numeric_dtype(df[target]):
        raise ValueError("Regression requires a numeric target.")
    warnings = []
    if "classification" in problem:
        counts = df[target].value_counts()
        if counts.min() < 4: warnings.append("At least one class has fewer than four samples; metrics may be unstable.")
        if counts.max() / counts.sum() > .8: warnings.append("The target is highly imbalanced; review balanced accuracy and F1.")
    return warnings


@dataclass
class Trained:
    pipeline: Any
    label_encoder: LabelEncoder | None
    features: list[str]
    target: str
    problem_type: str
    predictions: pd.DataFrame
    metrics: dict
    importance: list[dict]
    summary: dict
    warnings: list[str]


def train(df: pd.DataFrame, target: str, features: list[str], problem: str, cfg: dict, progress=lambda *_: None) -> Trained:
    started = datetime.now(timezone.utc)
    warnings = validate_training(df, target, features, problem)
    work = df[features + [target]].dropna(subset=[target]).copy()
    numeric = [c for c in features if pd.api.types.is_numeric_dtype(work[c])]
    categorical = [c for c in features if c not in numeric]
    if cfg.get("numeric_missing") == "drop": work = work.dropna(subset=numeric)
    if cfg.get("categorical_missing") == "drop": work = work.dropna(subset=categorical)
    if len(work) < 10: raise ValueError("Too few usable rows remain after preprocessing (minimum 10).")
    progress("preprocessing", 18, "Building a leakage-safe preprocessing pipeline")
    num_imputer = {"median": "median", "mean": "mean", "zero": "constant"}.get(cfg.get("numeric_missing"), "median")
    num_steps = [("imputer", SimpleImputer(strategy=num_imputer, fill_value=0))]
    scaling = cfg.get("scaling", "none")
    if scaling == "standard": num_steps.append(("scale", StandardScaler()))
    elif scaling == "minmax": num_steps.append(("scale", MinMaxScaler()))
    cat_imputer = SimpleImputer(strategy="constant" if cfg.get("categorical_missing") == "constant" else "most_frequent", fill_value="Unknown")
    if cfg.get("encoding") == "ordinal":
        encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    else:
        try:
            encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
        except TypeError:  # scikit-learn < 1.2 uses the former option name.
            encoder = OneHotEncoder(handle_unknown="ignore", sparse=True)
    preprocess = ColumnTransformer([("numeric", Pipeline(num_steps), numeric), ("categorical", Pipeline([("imputer", cat_imputer), ("encode", encoder)]), categorical)])
    classification = "classification" in problem
    label_encoder = LabelEncoder() if classification else None
    y = label_encoder.fit_transform(work[target]) if classification else pd.to_numeric(work[target])
    stratify = y if classification and cfg.get("stratify", True) else None
    try:
        X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
            work[features], y, work.index, test_size=float(cfg.get("test_size", .2)),
            random_state=int(cfg.get("random_seed", 42)), shuffle=bool(cfg.get("shuffle", True)), stratify=stratify,
        )
    except ValueError as exc:
        raise ValueError(f"Train-test split failed: {exc}") from exc
    params = {k: cfg.get(k) for k in ("n_estimators","learning_rate","max_depth","subsample","colsample_bytree","min_child_weight","gamma","reg_alpha","reg_lambda") if cfg.get(k) is not None}
    params.update(random_state=int(cfg.get("random_seed", 42)), n_jobs=-1, tree_method="hist")
    model = XGBClassifier(**params, eval_metric="logloss") if classification else XGBRegressor(**params, objective="reg:squarederror")
    pipeline = Pipeline([("preprocess", preprocess), ("model", model)])
    progress("training", 35, "Fitting XGBoost on training data only")
    tuning = cfg.get("tuning", "none")
    tuning_summary = {"method": tuning}
    if tuning != "none":
        space = {"model__n_estimators": [150, 500], "model__learning_rate": [.03, .1], "model__max_depth": [3, 8], "model__subsample": [.8], "model__colsample_bytree": [.8]}
        scoring = "f1_weighted" if classification else "neg_root_mean_squared_error"
        folds = min(int(cfg.get("cv_folds", 3)), 5)
        search = GridSearchCV(pipeline, space, cv=folds, scoring=scoring, n_jobs=-1) if tuning == "grid" else RandomizedSearchCV(pipeline, space, n_iter=min(int(cfg.get("iterations", 10)), 30), cv=folds, scoring=scoring, random_state=params["random_state"], n_jobs=-1)
        progress("tuning", 45, f"Running bounded {tuning} search")
        search.fit(X_train, y_train); pipeline = search.best_estimator_
        tuning_summary.update(best_params={k.replace("model__",""): json_value(v) for k,v in search.best_params_.items()}, best_cv_score=float(search.best_score_))
    else:
        pipeline.fit(X_train, y_train)
    progress("evaluating", 82, "Evaluating once on unseen test rows")
    pred_encoded = pipeline.predict(X_test)
    pred = label_encoder.inverse_transform(pred_encoded.astype(int)) if classification else pred_encoded
    actual = label_encoder.inverse_transform(np.asarray(y_test).astype(int)) if classification else np.asarray(y_test)
    result_df = df.loc[idx_test].copy()
    result_df["actual_target"] = actual; result_df["predicted_target"] = pred
    if classification:
        proba = pipeline.predict_proba(X_test)
        avg = "binary" if problem == "binary_classification" else "weighted"
        metrics = {
            "accuracy": accuracy_score(y_test, pred_encoded), "balanced_accuracy": balanced_accuracy_score(y_test, pred_encoded),
            "precision": precision_score(y_test, pred_encoded, average=avg), "recall": recall_score(y_test, pred_encoded, average=avg),
            "f1_score": f1_score(y_test, pred_encoded, average=avg), "matthews_correlation": matthews_corrcoef(y_test, pred_encoded),
            "log_loss": log_loss(y_test, proba),
        }
        if problem == "binary_classification": metrics["roc_auc"] = roc_auc_score(y_test, proba[:, 1])
        result_df["prediction_probability"] = proba.max(axis=1)
        result_df["prediction_correct"] = np.asarray(actual) == np.asarray(pred)
        primary, interpretation = metrics["accuracy"], f"The model correctly predicted {metrics['accuracy'] * 100:.1f}% of unseen test records."
    else:
        error = np.asarray(pred) - np.asarray(actual)
        mse = mean_squared_error(actual, pred)
        safe = np.asarray(actual) != 0
        metrics = {"r2": r2_score(actual,pred), "mae": mean_absolute_error(actual,pred), "mse": mse, "rmse": math.sqrt(mse), "median_absolute_error": median_absolute_error(actual,pred), "mape": float(np.mean(np.abs(error[safe] / np.asarray(actual)[safe])) * 100) if safe.any() else None}
        result_df["prediction_error"] = error; result_df["absolute_error"] = np.abs(error)
        primary, interpretation = metrics["rmse"], f"The model's root mean squared prediction error is approximately {metrics['rmse']:.3g} target units."
    raw_importance = pipeline.named_steps["model"].feature_importances_
    try:
        names = pipeline.named_steps["preprocess"].get_feature_names_out()
    except AttributeError:
        names = np.asarray([f"transformed_feature_{i + 1}" for i in range(len(raw_importance))])
    importance = sorted(({"feature": str(n).replace("numeric__","").replace("categorical__",""), "importance": float(v)} for n,v in zip(names, raw_importance)), key=lambda x:x["importance"], reverse=True)
    duration = (datetime.now(timezone.utc)-started).total_seconds()
    summary = {"problem_type": problem, "target_column": target, "training_rows": len(X_train), "test_rows": len(X_test), "original_features": len(features), "transformed_features": len(names), "train_test_split": f"{(1-float(cfg.get('test_size',.2)))*100:.0f}/{float(cfg.get('test_size',.2))*100:.0f}", "random_seed": params["random_state"], "tuning_method": tuning, "best_parameters": tuning_summary.get("best_params", params), "training_duration_seconds": round(duration,3), "primary_score": round(float(primary),5), "trained_at": started.isoformat()}
    progress("completed", 100, "Training and evaluation completed")
    return Trained(pipeline,label_encoder,features,target,problem,result_df,{k:json_value(v) for k,v in metrics.items()},importance,summary,warnings), interpretation, tuning_summary
