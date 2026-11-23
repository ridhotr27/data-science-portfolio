from __future__ import annotations

import re

import numpy as np
import pandas as pd

from ..utils.column_types import detect_kind, likely_identifier

PERCENT_PATTERN = re.compile(r"(percent|percentage|pct|rate|ratio)", re.I)


def issue(severity: str, code: str, title: str, detail: str, action: str, column: str | None = None, count: int | None = None) -> dict:
    return {"severity": severity, "code": code, "title": title, "detail": detail, "suggested_action": action, "column": column, "count": count}


def analyze_quality(frame: pd.DataFrame, overrides: dict[str, str] | None = None) -> dict:
    overrides = overrides or {}
    issues: list[dict] = []
    duplicate_count = int(frame.duplicated().sum())
    if duplicate_count:
        issues.append(issue("warning", "duplicate_rows", "Duplicate rows detected", f"{duplicate_count:,} rows exactly duplicate another row.", "Review duplicate records before deciding whether to remove them.", count=duplicate_count))
    incomplete_rows = int(frame.isna().any(axis=1).sum())
    for name in frame.columns:
        series = frame[name]
        kind = overrides.get(name, detect_kind(series))
        missing = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        if missing:
            severity = "critical" if missing == len(frame) else "warning"
            issues.append(issue(severity, "missing_values", f"Missing values in {name}", f"{missing:,} values ({missing / len(frame) * 100:.1f}%) are missing.", "Review whether to impute, retain, or remove affected records.", name, missing))
        if unique <= 1:
            issues.append(issue("warning", "constant_column", f"{name} is constant", "The column contains no variation and is unlikely to help modelling.", "Consider excluding this column from modelling.", name))
        elif series.value_counts(dropna=False, normalize=True).iloc[0] >= 0.98:
            issues.append(issue("information", "near_constant", f"{name} is near constant", "One value represents at least 98% of rows.", "Review whether this feature contains useful signal.", name))
        if likely_identifier(name, series):
            duplicate_ids = int(series.dropna().duplicated().sum())
            issues.append(issue("warning" if duplicate_ids else "information", "potential_id", f"{name} appears to be an identifier", f"It is nearly unique or has an identifier-like name. {duplicate_ids:,} duplicate non-null values were found.", "Exclude identifiers from modelling unless they carry intentional information.", name, duplicate_ids))
        if kind == "categorical" and unique > min(50, len(frame) * 0.5):
            issues.append(issue("warning", "high_cardinality", f"{name} has high cardinality", f"The column contains {unique:,} distinct categories.", "Consider grouping rare categories or excluding identifier-like values.", name, unique))
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            text = series.dropna().astype(str)
            whitespace = int(text.str.strip().eq("").sum())
            if whitespace:
                issues.append(issue("warning", "whitespace_values", f"{name} contains blank text", f"{whitespace:,} values contain only whitespace.", "Normalize blank text to missing values.", name, whitespace))
            if kind == "numeric":
                invalid = int((series.notna() & pd.to_numeric(series, errors="coerce").isna()).sum())
                if invalid:
                    issues.append(issue("critical", "invalid_numeric", f"{name} contains invalid numeric values", f"{invalid:,} non-empty values cannot be converted to numbers.", "Correct or explicitly mark these values as missing.", name, invalid))
            if kind == "date":
                invalid = int((series.notna() & pd.to_datetime(series, errors="coerce", format="mixed").isna()).sum())
                if invalid:
                    issues.append(issue("critical", "invalid_dates", f"{name} contains invalid dates", f"{invalid:,} non-empty values cannot be parsed as dates.", "Correct the date format or review the type override.", name, invalid))
            type_labels = text.map(lambda value: "numeric" if pd.notna(pd.to_numeric(value, errors="coerce")) else "text")
            if type_labels.nunique() > 1:
                issues.append(issue("warning", "mixed_types", f"{name} mixes numeric and text values", "The column contains both number-like and text values.", "Standardize values to one intended type.", name))
        if kind == "numeric":
            numeric = pd.to_numeric(series, errors="coerce")
            infinite = int(np.isinf(numeric).sum())
            if infinite:
                issues.append(issue("critical", "infinite_values", f"{name} contains infinite values", f"{infinite:,} values are positive or negative infinity.", "Replace infinities with valid values or missing markers.", name, infinite))
            finite = numeric.replace([np.inf, -np.inf], np.nan).dropna()
            if len(finite) >= 4:
                q1, q3 = finite.quantile([0.25, 0.75]); iqr = q3 - q1
                if iqr > 0:
                    extreme = int(((finite < q1 - 3 * iqr) | (finite > q3 + 3 * iqr)).sum())
                    if extreme:
                        issues.append(issue("information", "extreme_values", f"{name} contains suspiciously extreme values", f"{extreme:,} values lie beyond three IQRs from the quartiles.", "Inspect these records; unusual values can still be valid business data.", name, extreme))
            if PERCENT_PATTERN.search(name) and len(finite):
                impossible = int(((finite < 0) | (finite > 100)).sum())
                if impossible:
                    issues.append(issue("warning", "impossible_percentage", f"{name} has values outside 0–100", f"{impossible:,} values fall outside the usual percentage range.", "Confirm whether this column uses percentages, proportions, or another unit.", name, impossible))
    rank = {"critical": 0, "warning": 1, "information": 2}
    issues.sort(key=lambda item: (rank[item["severity"]], item["column"] or "", item["code"]))
    counts = {severity: sum(item["severity"] == severity for item in issues) for severity in rank}
    return {
        "issues": issues, "counts": counts, "duplicate_rows": duplicate_count,
        "complete_rows": len(frame) - incomplete_rows, "incomplete_rows": incomplete_rows,
    }
