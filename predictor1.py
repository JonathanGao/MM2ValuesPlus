from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable
import math
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------
# predict_item() always returns this dataclass. Field types and valid ranges:
#   item              str   Display name from the last matching history row.
#   current_value     float Latest observed value, after MM2 rounding (>= 0).
#   predicted_value   float Forecast at `horizon` steps ahead, after rounding.
#   change_pct        float Percent change from current to predicted (1 decimal).
#   direction         str   One of: "Rising", "Falling", "Stable".
#   confidence        str   One of: "High", "Medium", "Low" (label for the score).
#   confidence_score  int   Integer 0–100 quality score, not a probability.
#   lower_bound       float Rounded lower end of the expected range.
#   upper_bound       float Rounded upper end of the expected range.
#   observations      int   Number of usable (dated, numeric) history rows.
#   method            str   Algorithm tag, e.g. "weighted linear trend".
@dataclass
class PredictionResult:
    item: str
    current_value: float
    predicted_value: float
    change_pct: float
    direction: str
    confidence: str
    confidence_score: int
    lower_bound: float
    upper_bound: float
    observations: int
    method: str = "weighted linear trend"

    def to_dict(self) -> dict:
        """Convert to a plain dict for JSON/UI rendering. No extra requirements."""
        return asdict(self)


def _round_mm2(value: float) -> int:
    """
    Round to useful MM2-style increments instead of false precision.

    Parameters
    ----------
    value : float
        Any numeric value. Non-numeric input will raise when cast to float.
        Negative values are clamped to 0 before rounding.

    Rounding rules
    --------------
    0 <= value < 1      round to 3 decimal places (may return a float)
    1 <= value < 100    nearest 1
    100 <= value < 1e3  nearest 5
    1e3 <= value < 1e4  nearest 25
    value >= 1e4        nearest 100
    """
    value = max(0.0, float(value))
    if value < 100:
        step = 1
    elif value < 1_000:
        step = 5
    elif value < 10_000:
        step = 25
    else:
        step = 100
    if value >= 1:
         return int(round(value / step) * step)
    else:
        return round(value, 3)


def predict_item(records: Iterable[dict], item_name: str, horizon: int = 1) -> PredictionResult:
    """
    Predict the item's value `horizon` snapshots ahead of the latest observation.

    Parameters
    ----------
    records : Iterable[dict]
        History rows. Each dict must include:
          - item  : name of the item (compared case-insensitively to item_name)
          - date  : anything pandas.to_datetime can parse (ISO strings, timestamps)
          - value : numeric or numeric-string; non-numeric rows are dropped
        Optional:
          - demand : currently unused; accepted if present but ignored
        Extra columns are ignored. Duplicate dates keep the last row after sorting.
        Must contain at least one row whose `item` matches `item_name` and whose
        date/value parse successfully. Two or more such rows are required for a
        real trend; otherwise a low-confidence "hold current value" fallback is used.

    item_name : str
        Item to forecast. Matching is case-insensitive. Must match at least one
        record after converting both sides to string. Leading/trailing differences
        in spelling (not just case) will miss and raise ValueError.

    horizon : int, default 1
        How many future updates to forecast. Must be convertible to int.
        Values below 1 are treated as 1. There is no upper cap on horizon itself,
        but the allowed move from current value is capped at 40% for horizon >= 2.

    Returns
    -------
    PredictionResult
        See class docstring for field meanings.

    Raises
    ------
    ValueError
        If required columns are missing, or no usable history exists for item_name.
    """
    # --- Load and require columns ---
    # Build a working copy so callers' records are not mutated.
    df = pd.DataFrame(records).copy()
    required = {"item", "date", "value"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")

    # --- Filter to the requested item ---
    # Casefold so "Raygun" and "raygun" match. Non-string item values are stringified.
    df = df[df["item"].astype(str).str.casefold() == item_name.casefold()].copy()
    if df.empty:
        raise ValueError(f"No history found for '{item_name}'")

    # --- Parse, drop invalid rows, sort, dedupe ---
    # Unparseable dates/values become NaN and are removed. Oldest → newest order.
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"]).sort_values("date")
    # If multiple values exist for one date, use the last imported observation.
    df = df.drop_duplicates(subset=["date"], keep="last")

    # --- Insufficient history: cannot fit a line with < 2 points ---
    # Return the latest value unchanged, Low confidence, and a +/-10% range.
    if len(df) < 2:
        current = _round_mm2(df["value"].iloc[-1])
        return PredictionResult(
            item=item_name, current_value=current, predicted_value=current,
            change_pct=0.0, direction="Stable", confidence="Low",
            confidence_score=20, lower_bound=_round_mm2(current * 0.90),
            upper_bound=_round_mm2(current * 1.10), observations=len(df),
            method="insufficient-history fallback"
        )

    # --- Extract the value series ---
    # `current` is the most recent observation (last row after chronological sort).
    values = df["value"].to_numpy(dtype=float)
    current = float(values[-1])
    n = len(values)

    # --- Fit a weighted linear trend on recent history ---
    # Use at most the 8 most recent snapshots so the prediction reacts to current trends.
    # x is an index 0..window-1 (not calendar time), so horizon is in "updates" not days.
    # Weights 1, 2, ..., window give newer points more influence on slope/intercept.
    window = min(8, n)
    y = values[-window:]
    x = np.arange(window, dtype=float)
    weights = np.arange(1, window + 1, dtype=float)  # newer points matter more

    slope, intercept = np.polyfit(x, y, 1, w=weights)
    # Last observed x is (window - 1). Add horizon steps beyond that.
    raw_prediction = intercept + slope * (window - 1 + max(1, int(horizon)))

    # --- Guardrail: keep the forecast from jumping unrealistically ---
    # Cap one-step movement to +/-20%; scale moderately for longer horizons (max 40%).
    max_move = min(0.20 * max(1, int(horizon)), 0.40)
    predicted = float(np.clip(raw_prediction, current * (1-max_move), current * (1+max_move)))

    # --- Residual error of the fitted line on the same window ---
    # Used later for confidence and the expected-value interval, not for the point forecast.
    fitted = intercept + slope * x
    residuals = y - fitted
    mae = float(np.mean(np.abs(residuals)))
    residual_ratio = mae / max(abs(current), 1.0)

    # --- Confidence components (each clipped/scaled to 0–1) ---
    # Trend fit: 1.0 is a clean line, 0.0 means trend explains little.
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    fit_score = float(np.clip(r2, 0.0, 1.0))
    history_score = min(n / 8.0, 1.0)  # full credit at 8+ observations
    error_score = float(np.clip(1.0 - residual_ratio / 0.15, 0.0, 1.0))  # 0 if MAE >= 15% of current

    # --- Combine into a 0–100 score and a High/Medium/Low label ---
    # Confidence is an explainable heuristic, not a statistical probability.
    # Weights: 40% history length, 35% trend fit, 25% residual error.
    confidence_score = int(round(100 * (0.40*history_score + 0.35*fit_score + 0.25*error_score)))
    if confidence_score >= 75:
        confidence = "High"
    elif confidence_score >= 50:
        confidence = "Medium"
    else:
        confidence = "Low"

    # --- Expected range around the (already capped) prediction ---
    # Wider interval for noisier history and lower confidence; width is 5%–30%.
    interval_pct = float(np.clip(max(0.05, 2.0*residual_ratio + (100-confidence_score)/500), 0.05, 0.30))
    lower = predicted * (1-interval_pct)
    upper = predicted * (1+interval_pct)

    # --- Direction label from percent change ---
    # Moves within +/-2% of current are called Stable; beyond that Rising or Falling.
    change_pct = 100.0 * (predicted-current) / max(abs(current), 1.0)
    threshold = 2.0
    direction = "Rising" if change_pct > threshold else "Falling" if change_pct < -threshold else "Stable"

    # --- Assemble the public result (values rounded for display) ---
    return PredictionResult(
        item=str(df["item"].iloc[-1]),
        current_value=_round_mm2(current),
        predicted_value=_round_mm2(predicted),
        change_pct=round(change_pct, 1),
        direction=direction,
        confidence=confidence,
        confidence_score=confidence_score,
        lower_bound=_round_mm2(lower),
        upper_bound=_round_mm2(upper),
        observations=n,
    )


def predict_from_csv(path: str, item_name: str, horizon: int = 1) -> PredictionResult:
    """
    Load a CSV then call predict_item(). Same forecast as predict_item().

    Parameters
    ----------
    path : str
        Filesystem path to a CSV. Must be readable by pandas.read_csv.
        Must include columns: item, date, value. See predict_item() for row rules.

    item_name : str
        Same requirements as predict_item(item_name).

    horizon : int, default 1
        Same requirements as predict_item(horizon).
    """
    return predict_item(pd.read_csv(path).to_dict("records"), item_name, horizon)
