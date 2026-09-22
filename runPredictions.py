"""
Daily predictions job:
  1) Score open forecasts against new daily actuals in weapons.db
  2) Run every registered predictor for every weapon and upsert forecasts
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from sqlManager import (
    WEAPONS_DB,
    WEAPONS_RARITIES,
    EXCLUDED_GODLIES,
    EXCLUDED_CHROMAS,
    PREDICTIONS_TABLE,
    createTablePredictions,
    upsertPrediction,
    getUnscoredPredictions,
    getActualDailyValue,
    scorePrediction,
    loadWeaponHistoryRecords,
    listWeaponNames,
)
from predictors import PREDICTORS

HORIZON = 1


def _utcNow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _utcToday() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _targetDateForHorizon(horizon: int = HORIZON) -> str:
    """Horizon is in daily-scrape steps; target is that many UTC days ahead."""
    return (datetime.now(timezone.utc) + timedelta(days=max(1, int(horizon)))).strftime("%Y-%m-%d")


def scoreOpenPredictions(cursor) -> int:
    """Fill actualValue / errors for predictions whose target day now has a daily scrape."""
    unscored = getUnscoredPredictions(cursor)
    scored = 0
    for pred in unscored:
        rarity = pred["rarity"]
        if rarity not in WEAPONS_RARITIES:
            continue
        table = WEAPONS_RARITIES[rarity]
        actual = getActualDailyValue(cursor, table, pred["item"], pred["targetDate"])
        if actual is None:
            continue
        actualValue, _createdAt = actual
        scorePrediction(
            cursor,
            predictionId=pred["id"],
            actualValue=actualValue,
            predictedValue=pred["predictedValue"],
            direction=pred["direction"],
            currentValue=pred["currentValue"],
        )
        scored += 1
    return scored


def runForecasts(cursor, horizon: int = HORIZON) -> int:
    """Run every predictor for every weapon; upsert into predictions."""
    predictedAt = _utcNow()
    targetDate = _targetDateForHorizon(horizon)
    written = 0

    # Run for each rarity in the database
    for rarityKey, table in WEAPONS_RARITIES.items():
        names = listWeaponNames(cursor, table)
        if table == WEAPONS_RARITIES["godlies"]:
            names = [n for n in names if n not in EXCLUDED_GODLIES]
        elif table == WEAPONS_RARITIES["chromas"]:
            names = [n for n in names if n not in EXCLUDED_CHROMAS]

        print(f"  Forecasting {len(names)} {rarityKey} across {len(PREDICTORS)} predictor(s)")

        # For each weapon in the table
        for name in names:
            history = loadWeaponHistoryRecords(cursor, table, name)
            if not history:
                continue

            # Run for each prediction model
            for predictorId, predictFn in PREDICTORS.items():
                # predictFn is the prediction function --> Run the function
                try:
                    result = predictFn(history, name, horizon=horizon)
                except Exception as e:
                    print(f"    Skip {rarityKey}/{name} ({predictorId}): {e}")
                    continue

                # Upsert the prediction into the predictions table
                upsertPrediction(cursor, {
                    "predictor": predictorId,
                    "rarity": rarityKey,
                    "item": result.item,
                    "predictedAt": predictedAt,
                    "targetDate": targetDate,
                    "horizon": horizon,
                    "currentValue": result.current_value,
                    "predictedValue": result.predicted_value,
                    "changePct": result.change_pct,
                    "direction": result.direction,
                    "confidence": result.confidence,
                    "confidenceScore": result.confidence_score,
                    "lowerBound": result.lower_bound,
                    "upperBound": result.upper_bound,
                    "observations": result.observations,
                })
                written += 1

    return written


def main():
    print(f"=== Predictions run starting ({_utcNow()} UTC) ===")
    print(f"  Predictors: {', '.join(PREDICTORS.keys())}")
    print(f"  Today={_utcToday()} targetDate={_targetDateForHorizon(HORIZON)} horizon={HORIZON}")

    connection = sqlite3.connect(WEAPONS_DB)
    cursor = connection.cursor()
    createTablePredictions(cursor, PREDICTIONS_TABLE)

    scored = scoreOpenPredictions(cursor)
    connection.commit()
    print(f"  Scored {scored} open prediction(s)")

    written = runForecasts(cursor, horizon=HORIZON)
    connection.commit()
    print(f"  Upserted {written} forecast(s)")

    connection.close()
    print("=== Predictions run finished ===")


if __name__ == "__main__":
    main()
