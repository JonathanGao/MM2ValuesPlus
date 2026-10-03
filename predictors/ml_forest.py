"""Random-forest forecast compatible with predictor1.predict_item."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from predictor1 import PredictionResult, _round_mm2

LAGS = 7
MIN_TRAIN_ROWS = 24


def _features(values: np.ndarray, end: int) -> list[float]:
    """Use only values known at observation `end`."""
    current = float(values[end])
    scale = max(abs(current), 1.0)
    previous = values[end - LAGS:end]
    changes = np.diff(values[end - LAGS:end + 1]) / scale

    return [
        np.log1p(max(current, 0.0)),
        *[(current - float(v)) / scale for v in previous[::-1]],
        float(np.mean(changes[-3:])),
        float(np.mean(changes)),
        float(np.std(changes)),
    ]


def _forest() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=80,
        max_depth=5,
        min_samples_leaf=2,
        max_features=0.8,
        random_state=42,
        n_jobs=1,
    )


def predict_item(records, item_name: str, horizon: int = 1) -> PredictionResult:
    """Predict the same future item value and horizon as the existing model."""
    horizon = max(1, int(horizon))
    df = pd.DataFrame(records).copy()

    missing = {"item", "date", "value"} - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")

    df = df[
        df["item"].astype(str).str.casefold() == item_name.casefold()
    ].copy()
    if df.empty:
        raise ValueError(f"No history found for '{item_name}'")

    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"]).sort_values(
        "date", kind="stable"
    )
    df = df.drop_duplicates(subset=["date"], keep="last")
    # Both checks are NumPy arrays so they line up by row position.
    # The frame's index is no longer 0, 1, 2, ... after the item filter,
    # and mixing an array with a Series would match the wrong rows.
    values_array = df["value"].to_numpy()
    df = df[np.isfinite(values_array) & (values_array >= 0)]

    if df.empty:
        raise ValueError(f"No usable history found for '{item_name}'")

    values = df["value"].to_numpy(dtype=float)
    current = float(values[-1])
    n = len(values)

    # Each training example uses information available at `end`.
    # Its label is the change in value `horizon` observations later.
    end_indices = range(LAGS, n - horizon)
    x = np.asarray(
        [_features(values, end) for end in end_indices],
        dtype=float,
    )
    y = np.asarray(
        [
            (values[end + horizon] - values[end])
            / max(abs(values[end]), 1.0)
            for end in end_indices
        ],
        dtype=float,
    )

    if len(y) < MIN_TRAIN_ROWS:
        raise ValueError(
            f"ML requires {MIN_TRAIN_ROWS} labelled examples for "
            f"horizon {horizon}; found {len(y)}"
        )

    # Estimate error on the most recent chronological holdout.
    validation_size = max(5, min(20, len(y) // 5))
    validation_model = _forest().fit(
        x[:-validation_size], y[:-validation_size]
    )
    validation_errors = np.abs(
        validation_model.predict(x[-validation_size:])
        - y[-validation_size:]
    )

    error_ratio = float(np.median(validation_errors))
    interval_pct = float(
        np.clip(np.quantile(validation_errors, 0.8), 0.05, 0.30)
    )
    score = int(
        round(
            100
            * np.clip(1.0 - error_ratio / 0.20, 0.0, 1.0)
            * min(len(y) / 60.0, 1.0)
        )
    )
    confidence = (
        "High" if score >= 75
        else "Medium" if score >= 50
        else "Low"
    )

    # Refit using all labelled examples, then forecast from the latest value.
    model = _forest().fit(x, y)
    change = float(
        model.predict(np.asarray([_features(values, n - 1)]))[0]
    )

    # Match the existing model's movement cap and output conventions.
    max_move = min(0.20 * horizon, 0.40)
    predicted = float(
        np.clip(
            current + change * max(abs(current), 1.0),
            current * (1 - max_move),
            current * (1 + max_move),
        )
    )
    change_pct = 100.0 * (predicted - current) / max(abs(current), 1.0)
    direction = (
        "Rising" if change_pct > 2
        else "Falling" if change_pct < -2
        else "Stable"
    )

    return PredictionResult(
        item=str(df["item"].iloc[-1]),
        current_value=_round_mm2(current),
        predicted_value=_round_mm2(predicted),
        change_pct=round(change_pct, 1),
        direction=direction,
        confidence=confidence,
        confidence_score=score,
        lower_bound=_round_mm2(predicted * (1 - interval_pct)),
        upper_bound=_round_mm2(predicted * (1 + interval_pct)),
        observations=n,
        method="random forest direct forecast",
    )
