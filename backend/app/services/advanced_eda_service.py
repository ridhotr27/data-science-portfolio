from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from ..utils.column_types import detect_kind, likely_identifier
from ..utils.problem_type import suggest_problem
from ..utils.serialization import json_value, records
from .data_quality_service import analyze_quality
from .eda_profiling_service import detailed_profile


def effective_kind(frame: pd.DataFrame, column: str, overrides: dict[str, str]) -> str:
    if column not in frame:
        raise ValueError(f"Unknown column: {column}")
    return overrides.get(column, detect_kind(frame[column]))


def numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()


def distribution(frame: pd.DataFrame, column: str, overrides: dict[str, str], bins: int, top_n: int, date_frequency: str) -> dict:
    kind = effective_kind(frame, column, overrides)
    series = frame[column]
    result: dict[str, Any] = {"column": column, "type": kind, "missing": int(series.isna().sum())}
    if kind == "numeric":
        values = numeric_series(series)
        if values.empty: raise ValueError("The selected column has no valid numeric values.")
        counts, edges = np.histogram(values, bins=min(bins, max(5, int(math.sqrt(len(values)) * 2))))
        q1, q3 = values.quantile([.25, .75]); iqr = q3 - q1
        result.update({
            "histogram": [{"start": json_value(edges[i]), "end": json_value(edges[i + 1]), "count": int(counts[i])} for i in range(len(counts))],
            "summary": {"minimum": json_value(values.min()), "maximum": json_value(values.max()), "mean": json_value(values.mean()), "median": json_value(values.median()), "standard_deviation": json_value(values.std()), "q1": json_value(q1), "q3": json_value(q3), "iqr": json_value(iqr), "skewness": json_value(stats.skew(values, bias=False)) if len(values) > 2 else None, "kurtosis": json_value(stats.kurtosis(values, bias=False)) if len(values) > 3 else None, "zero_pct": round(float((values == 0).mean() * 100), 2), "negative_pct": round(float((values < 0).mean() * 100), 2)},
        })
    elif kind == "date":
        parsed = pd.to_datetime(series, errors="coerce", format="mixed").dropna()
        aliases = {"day": "D", "week": "W", "month": "ME", "quarter": "QE", "year": "YE"}
        counts = parsed.dt.to_period(aliases[date_frequency].replace("E", "")).value_counts().sort_index()
        result["series"] = [{"period": str(period), "count": int(count)} for period, count in counts.items()]
        result["summary"] = {"earliest": json_value(parsed.min()), "latest": json_value(parsed.max()), "valid": len(parsed)}
    else:
        counts = series.fillna("(Missing)").astype(str).value_counts()
        top = counts.head(top_n)
        other = int(counts.iloc[top_n:].sum())
        categories = [{"value": str(value)[:100], "count": int(count), "pct": round(int(count) / len(series) * 100, 2)} for value, count in top.items()]
        if other: categories.append({"value": "Other", "count": other, "pct": round(other / len(series) * 100, 2)})
        result.update(categories=categories, summary={"unique": int(series.nunique(dropna=True)), "rare_categories": int((counts < max(2, len(series) * .01)).sum())})
    return result


def correlation(frame: pd.DataFrame, overrides: dict[str, str], method: str, threshold: float, selected: list[str] | None = None) -> dict:
    names = selected or [name for name in frame if effective_kind(frame, name, overrides) == "numeric"]
    if len(names) < 2: raise ValueError("Select at least two numeric columns.")
    if len(names) > 40: raise ValueError("Correlation is limited to 40 selected numeric columns.")
    numeric = frame[names].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    matrix = numeric.corr(method=method)
    pairs = []
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            value = matrix.loc[left, right]
            if pd.notna(value) and abs(value) >= threshold:
                pairs.append({"x": left, "y": right, "correlation": float(value), "strength": "positive" if value > 0 else "negative"})
    pairs.sort(key=lambda item: abs(item["correlation"]), reverse=True)
    return {"method": method, "columns": names, "matrix": [{"column": name, **{other: json_value(matrix.loc[name, other]) for other in names}} for name in names], "strong_pairs": pairs}


def relationship(frame: pd.DataFrame, x: str, y: str, group: str | None, overrides: dict[str, str]) -> dict:
    x_kind, y_kind = effective_kind(frame, x, overrides), effective_kind(frame, y, overrides)
    if group and group not in frame: raise ValueError(f"Unknown group column: {group}")
    work = frame[[x, y] + ([group] if group else [])].dropna().head(5000)
    if x_kind == "numeric" and y_kind == "numeric":
        sample = work.sample(min(500, len(work)), random_state=42)
        return {"chart": "scatter", "x": x, "y": y, "points": records(sample), "summary": {"pearson": json_value(pd.to_numeric(work[x], errors="coerce").corr(pd.to_numeric(work[y], errors="coerce"))), "rows": len(work)}}
    if x_kind == "date" and y_kind == "numeric":
        dates = pd.to_datetime(work[x], errors="coerce", format="mixed")
        numeric = pd.to_numeric(work[y], errors="coerce")
        grouped = pd.DataFrame({"date": dates, "value": numeric}).dropna().set_index("date").resample("ME").mean().reset_index()
        return {"chart": "line", "x": x, "y": y, "points": [{"x": json_value(row.date), "value": json_value(row.value)} for row in grouped.itertuples()], "summary": {"aggregation": "monthly mean", "rows": len(work)}}
    if x_kind in {"categorical", "boolean"} and y_kind == "numeric":
        work[y] = pd.to_numeric(work[y], errors="coerce")
        grouped = work.groupby(x, dropna=False)[y].agg(["mean", "median", "count"]).sort_values("count", ascending=False).head(20).reset_index()
        return {"chart": "bar", "x": x, "y": y, "points": records(grouped), "summary": {"aggregation": "mean and median", "rows": len(work)}}
    table = pd.crosstab(work[x], work[y]).iloc[:20, :20]
    return {"chart": "contingency", "x": x, "y": y, "columns": [str(value) for value in table.columns], "points": [{"value": str(index), **{str(key): int(value) for key, value in row.items()}} for index, row in table.iterrows()], "summary": {"rows": len(work)}}


def outliers(frame: pd.DataFrame, overrides: dict[str, str], method: str, threshold: float, selected: str | None, limit: int) -> dict:
    names = [selected] if selected else [name for name in frame if effective_kind(frame, name, overrides) == "numeric"]
    summaries, masks = [], {}
    for name in names:
        values = pd.to_numeric(frame[name], errors="coerce").replace([np.inf, -np.inf], np.nan)
        if method == "zscore":
            center, spread = values.mean(), values.std()
            mask = (values - center).abs() > threshold * spread if spread and pd.notna(spread) else pd.Series(False, index=frame.index)
            lower, upper = center - threshold * spread, center + threshold * spread
        else:
            q1, q3 = values.quantile([.25, .75]); spread = q3 - q1
            lower, upper = q1 - threshold * spread, q3 + threshold * spread
            mask = (values < lower) | (values > upper)
        masks[name] = mask.fillna(False)
        count = int(mask.sum())
        summaries.append({"column": name, "lower": json_value(lower), "upper": json_value(upper), "count": count, "pct": round(count / len(frame) * 100, 2)})
    combined = pd.concat(masks, axis=1).any(axis=1) if masks else pd.Series(False, index=frame.index)
    rows = frame.loc[combined].head(limit).copy()
    rows.insert(0, "_row_number", rows.index + 1)
    return {"method": method, "threshold": threshold, "summary": summaries, "total_rows": int(combined.sum()), "rows": records(rows)}


def target_analysis(frame: pd.DataFrame, target: str, overrides: dict[str, str], requested: str) -> dict:
    kind = effective_kind(frame, target, overrides)
    suggestion = suggest_problem(frame[target])
    problem = suggestion["type"] if requested == "auto" else requested
    base = {"target": target, "problem_type": problem, "suggestion": suggestion}
    if "regression" in problem:
        base["distribution"] = distribution(frame, target, {**overrides, target: "numeric"}, 20, 10, "month")
        numeric = [name for name in frame if name != target and effective_kind(frame, name, overrides) == "numeric"]
        correlations = frame[numeric + [target]].apply(pd.to_numeric, errors="coerce").corr()[target].drop(target).abs().sort_values(ascending=False)
        base["feature_relationships"] = [{"feature": name, "absolute_correlation": json_value(value)} for name, value in correlations.head(15).items()]
    else:
        counts = frame[target].fillna("(Missing)").astype(str).value_counts()
        base["classes"] = [{"value": str(value), "count": int(count), "pct": round(count / len(frame) * 100, 2)} for value, count in counts.items()]
        base["imbalance_ratio"] = json_value(counts.max() / counts.min()) if len(counts) > 1 and counts.min() else None
    return base


def readiness(frame: pd.DataFrame, overrides: dict[str, str], target: str | None = None) -> dict:
    quality = analyze_quality(frame, overrides)
    checks = []
    def add(name, level, detail): checks.append({"name": name, "level": level, "detail": detail})
    add("Missing values", "warning" if frame.isna().any().any() else "pass", f"{int(frame.isna().sum().sum()):,} missing cells")
    add("Duplicate data", "warning" if frame.duplicated().any() else "pass", f"{int(frame.duplicated().sum()):,} duplicate rows")
    ids = [name for name in frame if likely_identifier(name, frame[name])]
    add("Identifier columns", "warning" if ids else "pass", ", ".join(ids[:8]) or "None detected")
    constants = [name for name in frame if frame[name].nunique(dropna=True) <= 1]
    add("Constant columns", "warning" if constants else "pass", ", ".join(constants[:8]) or "None detected")
    add("Dataset shape", "warning" if len(frame.columns) >= len(frame) else "pass", f"{len(frame):,} rows and {len(frame.columns)} columns")
    if target and target in frame and detect_kind(frame[target]) != "numeric":
        counts = frame[target].value_counts()
        ratio = counts.min() / counts.sum() if len(counts) else 0
        add("Class balance", "warning" if ratio < .1 else "pass", f"Smallest class represents {ratio * 100:.1f}%")
    critical = quality["counts"]["critical"]
    warnings = quality["counts"]["warning"] + sum(item["level"] == "warning" for item in checks)
    status = "Requires data cleaning" if critical else "Ready with warnings" if warnings else "Ready"
    return {"status": status, "explanation": "Status is determined by critical data-quality findings first, then warning-level checks; it is not a predictive score.", "checks": checks, "quality_counts": quality["counts"]}


def insights(frame: pd.DataFrame, overrides: dict[str, str]) -> list[dict]:
    quality = analyze_quality(frame, overrides)
    output = [{"kind": "finding", "text": item["detail"], "source": item["code"]} for item in quality["issues"][:12]]
    numeric = [name for name in frame if effective_kind(frame, name, overrides) == "numeric"]
    if len(numeric) >= 2:
        corr = correlation(frame, overrides, "pearson", .8, numeric[:40])
        for pair in corr["strong_pairs"][:5]:
            output.append({"kind": "finding", "text": f"{pair['x']} and {pair['y']} have a {pair['strength']} Pearson correlation of {pair['correlation']:.2f}. Correlation does not prove causation.", "source": "correlation"})
    for name in numeric[:20]:
        values = numeric_series(frame[name])
        if len(values) > 3:
            skew = stats.skew(values, bias=False)
            if abs(skew) > 1:
                output.append({"kind": "finding", "text": f"{name} is strongly {'right' if skew > 0 else 'left'}-skewed (skewness {skew:.2f}).", "source": "distribution"})
    return output[:20]
