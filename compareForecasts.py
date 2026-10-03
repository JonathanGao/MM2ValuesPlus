"""Compare scored forecasts from the existing and ML models."""
from __future__ import annotations

import argparse
import sqlite3

from sqlManager import WEAPONS_DB

BASELINE = "weighted_linear_trend"
ML = "random_forest_direct"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=1)
    args = parser.parse_args()

    if args.horizon < 1:
        parser.error("--horizon must be at least 1")

    with sqlite3.connect(WEAPONS_DB) as connection:
        try:
            rows = connection.execute(
                """
                SELECT b.actualValue,
                       b.predictedValue,
                       m.predictedValue,
                       b.directionCorrect,
                       m.directionCorrect
                FROM predictions AS b
                JOIN predictions AS m
                  ON b.rarity = m.rarity
                 AND b.item = m.item
                 AND b.targetDate = m.targetDate
                 AND b.horizon = m.horizon
                WHERE b.predictor = ?
                  AND m.predictor = ?
                  AND b.horizon = ?
                  AND b.actualValue IS NOT NULL
                  AND m.actualValue IS NOT NULL
                  AND b.actualValue = m.actualValue
                """,
                (BASELINE, ML, args.horizon),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            parser.error(f"Forecast table unavailable: {exc}")

    if not rows:
        print(
            "No matched, scored forecasts yet. Run the daily job "
            "and wait for the target day's actual value."
        )
        return

    print(
        f"Matched forecasts: {len(rows)}; "
        f"horizon: {args.horizon}"
    )
    print(
        "Model                  MAE        WAPE (%)   "
        "Direction correct (%)"
    )

    for label, prediction_col, direction_col in (
        ("Weighted linear trend", 1, 3),
        ("Random forest direct", 2, 4),
    ):
        errors = [
            abs(row[prediction_col] - row[0])
            for row in rows
        ]
        mae = sum(errors) / len(errors)
        wape = (
            100 * sum(errors)
            / max(sum(abs(row[0]) for row in rows), 1.0)
        )
        direction_accuracy = (
            100
            * sum(row[direction_col] or 0 for row in rows)
            / len(rows)
        )
        print(
            f"{label:<22} {mae:>8.3f} "
            f"{wape:>11.2f} {direction_accuracy:>23.1f}"
        )


if __name__ == "__main__":
    main()
