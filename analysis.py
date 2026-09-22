import sqlite3
import pandas as pd
from sqlManager import WEAPONS_RARITIES, WEAPONS_DB, isExcludedItem
from utils import displayErrorMessage
from predictors import DEFAULT_PREDICTOR

def checkExcluded(weaponName, rarity, app):
    if isExcludedItem(rarity, weaponName):
        return displayErrorMessage(f"Weapon {weaponName} is excluded from the analysis.", app)
    else:
        return False

def getWeaponJson(rarity, weaponName, app):
    # Placeholder godlies (e.g. Batwing on the godlies page) are excluded only there;
    # the real ancient Batwing must still be available via /api/ancients/Batwing.
    checkExcluded(weaponName, rarity, app)
    connection = sqlite3.connect(WEAPONS_DB)
    df = pd.read_sql_query(f'SELECT * FROM {WEAPONS_RARITIES[rarity]} WHERE name = "{weaponName}";', connection)
    if df.empty:
        return displayErrorMessage(f"Weapon {weaponName} does not exist.", app)
    return df.to_json(orient="records")

def getPredictions(rarity, weaponName, app, predictor=None):
    checkExcluded(weaponName, rarity, app)
    predictor = predictor or DEFAULT_PREDICTOR
    connection = sqlite3.connect(WEAPONS_DB)
    df = pd.read_sql_query(
        """
        SELECT * FROM predictions
        WHERE rarity = ? AND item = ? AND predictor = ?
        ORDER BY predictedAt ASC
        """,
        connection,
        params=(rarity, weaponName, predictor),
    )
    connection.close()
    if df.empty:
        return displayErrorMessage(f"Predictions for {weaponName} do not exist.", app)
    return df.to_json(orient="records")

def _formatMover(rarity, name, previousValue, currentValue, changePct, **extra):
    pct = float(changePct) if changePct is not None else 0.0
    return {
        "rarity": rarity,
        "name": name,
        "previousValue": previousValue,
        "currentValue": currentValue,
        "changePct": round(pct, 2),
        **extra,
    }

def getActualTopMovers(limit: int = 5):
    """Biggest day-over-day % moves from the two most recent daily scrapes."""
    connection = sqlite3.connect(WEAPONS_DB)
    cursor = connection.cursor()
    movers = []

    for rarity, table in WEAPONS_RARITIES.items():
        dates = [
            row[0]
            for row in cursor.execute(
                f"""
                SELECT DISTINCT date(createdAt)
                FROM {table}
                WHERE demand IS NOT NULL
                ORDER BY 1 DESC
                LIMIT 2
                """
            ).fetchall()
        ]
        if len(dates) < 2:
            continue

        latestDate, previousDate = dates[0], dates[1]
        rows = cursor.execute(
            f"""
            SELECT a.name, b.value, a.value,
                   CASE
                       WHEN b.value IS NULL OR b.value = 0 THEN NULL
                       ELSE 100.0 * (a.value - b.value) / ABS(b.value)
                   END AS changePct
            FROM {table} a
            JOIN {table} b ON a.name = b.name
            WHERE a.demand IS NOT NULL AND b.demand IS NOT NULL
              AND date(a.createdAt) = ?
              AND date(b.createdAt) = ?
              AND a.value IS NOT NULL AND b.value IS NOT NULL
            """,
            (latestDate, previousDate),
        ).fetchall()

        for name, previousValue, currentValue, changePct in rows:
            if isExcludedItem(rarity, name):
                continue
            if changePct is None or changePct == 0:
                continue
            movers.append(
                _formatMover(
                    rarity,
                    name,
                    previousValue,
                    currentValue,
                    changePct,
                    fromDate=previousDate,
                    toDate=latestDate,
                )
            )

    connection.close()
    movers.sort(key=lambda m: abs(m["changePct"]), reverse=True)
    return movers[:limit]

def getPredictedTopMovers(limit: int = 5, predictor: str | None = None):
    """Biggest expected % moves from each weapon's latest forecast for one model."""
    predictor = predictor or DEFAULT_PREDICTOR
    connection = sqlite3.connect(WEAPONS_DB)
    df = pd.read_sql_query(
        """
        SELECT p.rarity, p.item AS name, p.currentValue AS previousValue,
               p.predictedValue AS currentValue, p.changePct, p.direction, p.targetDate
        FROM predictions p
        INNER JOIN (
            SELECT rarity, item, MAX(predictedAt) AS maxPredictedAt
            FROM predictions
            WHERE predictor = ?
            GROUP BY rarity, item
        ) latest
          ON p.rarity = latest.rarity
         AND p.item = latest.item
         AND p.predictedAt = latest.maxPredictedAt
        WHERE p.predictor = ?
          AND p.changePct IS NOT NULL AND p.changePct != 0
        ORDER BY ABS(p.changePct) DESC
        """,
        connection,
        params=(predictor, predictor),
    )
    connection.close()

    movers = []
    for row in df.to_dict(orient="records"):
        if isExcludedItem(row["rarity"], row["name"]):
            continue
        movers.append(
            _formatMover(
                row["rarity"],
                row["name"],
                row["previousValue"],
                row["currentValue"],
                row["changePct"],
                direction=row.get("direction"),
                targetDate=row.get("targetDate"),
            )
        )
        if len(movers) >= limit:
            break
    return movers

def getTopMovers(limit: int = 5, predictor: str | None = None):
    predictor = predictor or DEFAULT_PREDICTOR
    return {
        "actual": getActualTopMovers(limit),
        "predicted": getPredictedTopMovers(limit, predictor=predictor),
    }
