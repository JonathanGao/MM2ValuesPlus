import sqlite3

from datetime import datetime, timezone, date
from pathlib import Path
from utils import formatValue

# Define rarities as they are defined in the database to avoid mixups
WEAPONS_RARITIES = {
    'legendaries': 'legendaries',
    'ancients': 'ancients',
    'chromas': 'chromas',
    'godlies': 'godlies',
}

DATABASES_DIR = Path(__file__).resolve().parent / "databases"
WEAPONS_DB = str(DATABASES_DIR / "weapons.db")
UPDATE_LOG_DB = str(DATABASES_DIR / "updateLog.db")

EXCLUDED_GODLIES = ['Black Luger', 'Mortal Blade', 'Batwing']

def createTableWeapons(cursor, tableName):
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {tableName} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL, -- either "supremevalues" or "mm2values"
    gameRarity TEXT NOT NULL, -- either "common", "uncommon", "rare", "legendary", "vintage", "godly", "ancient", or "chroma"
    tier INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    value INTEGER, 
    minRange INTEGER, 
    maxRange INTEGER,  
    stabilityScore INTEGER, 
    demand INTEGER, 
    rarity INTEGER, 
    flippability TEXT, 
    chanceOfRising INTEGER,
    createdAt TEXT NOT NULL default CURRENT_TIMESTAMP
);""")
    print("createTable function success")

def createTableUpdateLog(cursor, tableName):
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {tableName} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL, -- either "supremevalues" or "mm2values"
    log TEXT NOT NULL,
    createdAt TEXT default CURRENT_TIMESTAMP
);""")
    print("createTableUpdateLog function success")

def getWeaponRange(weaponsData):
    weaponRange = {}
    for i in weaponsData:
        weapon = weaponsData[i]
        # Range is a string, parse the string to separate it into the minimum and maximums of the range.
        Range = weapon["range"]
        minRange, maxRange = None, None
        if "-" in Range:
            rawParsedRange = list(map(lambda x: x.strip(), Range.split("-")))
            finalParsedRange = list(map(lambda x: formatValue(x), rawParsedRange))
            
            if finalParsedRange[0] > finalParsedRange[1]:
                minRange, maxRange = finalParsedRange[1], finalParsedRange[0]
            else:
                minRange, maxRange = finalParsedRange[0], finalParsedRange[1]
        else:
            value = formatValue(weapon["value"])
            minRange, maxRange = value, value
        weaponRange[weapon["name"]] = {
            "minRange": minRange,
            "maxRange": maxRange,
        }
    return weaponRange

def insertWeapons(cursor, weapons, weaponRange, weaponTable: str):
    for weapon in weapons:
        weaponData = weapons[weapon]
        weaponRangeMin = None
        weaponRangeMax = None
        if weaponRange[weapon]:
            weaponRangeMin, weaponRangeMax = weaponRange[weapon]["minRange"], weaponRange[weapon]["maxRange"]
        cursor.execute(f"""
        INSERT INTO {weaponTable} (name, source, gameRarity, tier, value, minRange, maxRange, stabilityScore, demand, rarity, flippability, chanceOfRising, createdAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            weaponData["name"],
            weaponData["source"],
            weaponData["gameRarity"],
            weaponData["tier"],
            weaponData["value"],
            weaponRangeMin,
            weaponRangeMax,
            weaponData["stabilityScore"],
            weaponData["demand"],
            weaponData["rarity"],
            weaponData["flippability"],
            weaponData["chanceOfRising"],
            weaponData["createdAt"],
        ))

def getExistingWeaponTimestamps(cursor, tableName: str, source: str = "supremevalues") -> set[tuple[str, str]]:
    """Return {(name, createdAt), ...} already stored for this source — used to skip history dupes."""
    cursor.execute(f"""
        SELECT name, createdAt FROM {tableName}
        WHERE source = ?
    """, (source,))
    return {(row[0], row[1]) for row in cursor.fetchall() if row[0] and row[1]}

def getExistingUpdateLogEntries(cursor, tableName: str, source: str = "supremevalues") -> set[tuple[str, str]]:
    """Return {(log, createdAt), ...} already stored for this source — used to skip update-log dupes."""
    cursor.execute(f"""
        SELECT log, createdAt FROM {tableName}
        WHERE source = ?
    """, (source,))
    return {(row[0], row[1]) for row in cursor.fetchall() if row[0] is not None and row[1]}

def insertWeaponRecords(cursor, records: list[dict], weaponTable: str) -> int:
    """
    Insert a list of weapon row dicts (one DB row each).
    Unlike insertWeapons, this supports multiple timestamps for the same weapon name
    (e.g. Supreme Values per-item value history).
    Each record must include name/source/gameRarity/tier/value/createdAt and may include
    minRange/maxRange/stabilityScore/demand/rarity/flippability/chanceOfRising.
    """
    inserted = 0
    for weaponData in records:
        cursor.execute(f"""
        INSERT INTO {weaponTable} (name, source, gameRarity, tier, value, minRange, maxRange, stabilityScore, demand, rarity, flippability, chanceOfRising, createdAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            weaponData["name"],
            weaponData["source"],
            weaponData["gameRarity"],
            weaponData["tier"],
            weaponData["value"],
            weaponData.get("minRange"),
            weaponData.get("maxRange"),
            weaponData.get("stabilityScore"),
            weaponData.get("demand"),
            weaponData.get("rarity"),
            weaponData.get("flippability"),
            weaponData.get("chanceOfRising"),
            weaponData["createdAt"],
        ))
        inserted += 1
    return inserted

def insertUpdateLog(cursor, updateLogs, updateLogTable: str):
    for updateLog in updateLogs:
        cursor.execute(f"""
        INSERT INTO {updateLogTable} (source, log, createdAt)
        VALUES (?, ?, ?)
        """, (
            updateLog["source"],
            updateLog["log"],
            updateLog["createdAt"],
        ))
    print("insertUpdateLog function success")

def scrapedToday(cursor, tableName: str, source: str = "supremevalues") -> bool:
    """
    True if we already have today's daily scrape for this table.
    For weapon tables, ignore value-history rows (demand IS NULL) so a history
    backfill cannot make the daily scraper think it already ran.

    If historicalData backfills a value from today it will not cause the daily scraper to skip, since backfill will not retrieve the demand.
    """
    if tableName in WEAPONS_RARITIES.values():
        cursor.execute(f"""
            SELECT 1 FROM {tableName}
            WHERE source = ? AND date(createdAt) = date('now', 'utc')
              AND demand IS NOT NULL
            LIMIT 1
        """, (source,))
    else:
        cursor.execute(f"""
            SELECT 1 FROM {tableName}
            WHERE source = ? AND date(createdAt) = date('now', 'utc')
            LIMIT 1
        """, (source,))
    return cursor.fetchone() is not None

def scrapedOnDate(cursor, tableName, date: date, source: str = "supremevalues"): 
    cursor.execute(f"""
    SELECT 1 FROM {tableName}
    WHERE source = ? AND date(createdAt) = date(?, 'utc')
    """, (source, date.strftime("%Y-%m-%d")))
    # Returns true if fetchone() gets a result and falose if it doesn't
    return cursor.fetchone() is not None

PREDICTIONS_TABLE = "predictions"

def createTablePredictions(cursor, tableName: str = PREDICTIONS_TABLE):
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {tableName} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        predictor TEXT NOT NULL,
        rarity TEXT NOT NULL,
        item TEXT NOT NULL,
        predictedAt TEXT NOT NULL,
        targetDate TEXT NOT NULL,
        horizon INTEGER NOT NULL,
        currentValue REAL,
        predictedValue REAL,
        changePct REAL,
        direction TEXT,
        confidence TEXT,
        confidenceScore INTEGER,
        lowerBound REAL,
        upperBound REAL,
        observations INTEGER,
        actualValue REAL,
        errorAbs REAL,
        errorPct REAL,
        directionCorrect INTEGER,
        UNIQUE (predictor, rarity, item, targetDate, horizon)
    );
    """)
    print("createTablePredictions function success")

def upsertPrediction(cursor, row: dict, tableName: str = PREDICTIONS_TABLE) -> None:
    """Insert or replace a forecast row. Does not clear scored actual/error fields on conflict
    unless the new row explicitly includes them."""
    cursor.execute(f"""
    INSERT INTO {tableName} (
        predictor, rarity, item, predictedAt, targetDate, horizon,
        currentValue, predictedValue, changePct, direction, confidence, confidenceScore,
        lowerBound, upperBound, observations,
        actualValue, errorAbs, errorPct, directionCorrect
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(predictor, rarity, item, targetDate, horizon) DO UPDATE SET
        predictedAt = excluded.predictedAt,
        currentValue = excluded.currentValue,
        predictedValue = excluded.predictedValue,
        changePct = excluded.changePct,
        direction = excluded.direction,
        confidence = excluded.confidence,
        confidenceScore = excluded.confidenceScore,
        lowerBound = excluded.lowerBound,
        upperBound = excluded.upperBound,
        observations = excluded.observations
    """, (
        row["predictor"],
        row["rarity"],
        row["item"],
        row["predictedAt"],
        row["targetDate"],
        row["horizon"],
        row.get("currentValue"),
        row.get("predictedValue"),
        row.get("changePct"),
        row.get("direction"),
        row.get("confidence"),
        row.get("confidenceScore"),
        row.get("lowerBound"),
        row.get("upperBound"),
        row.get("observations"),
        row.get("actualValue"),
        row.get("errorAbs"),
        row.get("errorPct"),
        row.get("directionCorrect"),
    ))

# Gets all the values from a table that have predictions that have not been scored yet.
def getUnscoredPredictions(cursor, tableName: str = PREDICTIONS_TABLE) -> list[dict]:
    cursor.execute(f"""
        SELECT id, predictor, rarity, item, targetDate, horizon,
               predictedValue, direction, currentValue
        FROM {tableName}
        WHERE actualValue IS NULL
        ORDER BY targetDate, rarity, item
    """)
    cols = ["id", "predictor", "rarity", "item", "targetDate", "horizon",
            "predictedValue", "direction", "currentValue"]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

# Gets the FIRST actual daily value after the target date.
def getActualDailyValue(cursor, rarityTable: str, item: str, targetDate: str):
    """
    First daily-scrape value (demand IS NOT NULL) on/after targetDate for this item.
    Returns (value, createdAt) or None.
    """
    cursor.execute(f"""
        SELECT value, createdAt FROM {rarityTable}
        WHERE name = ? AND demand IS NOT NULL AND date(createdAt) >= date(?)
        ORDER BY createdAt ASC
        LIMIT 1
    """, (item, targetDate))
    row = cursor.fetchone()
    if not row:
        return None
    return row[0], row[1]

def scorePrediction(cursor, predictionId: int, actualValue, predictedValue, direction: str,
                    currentValue, tableName: str = PREDICTIONS_TABLE) -> None:
    """Write actual + error metrics onto an existing prediction row."""
    actual = float(actualValue) if actualValue is not None else None
    predicted = float(predictedValue) if predictedValue is not None else None
    errorAbs = None
    errorPct = None
    directionCorrect = None
    if actual is not None and predicted is not None:
        errorAbs = abs(predicted - actual)
        # Denominator is either the |actual| or 1.0, whichever is greater.
        denom = max(abs(actual), 1.0)
        # Error is the error / actual(or 1.0 if the actual value is lower than 1)
        errorPct = 100.0 * errorAbs / denom
        # Direction correctness vs move from current → actual
        if currentValue is not None:
            current = float(currentValue)
            actualChangePct = 100.0 * (actual - current) / max(abs(current), 1.0)
            threshold = 2.0
            if actualChangePct > threshold:
                actualDirection = "Rising"
            elif actualChangePct < -threshold:
                actualDirection = "Falling"
            else:
                actualDirection = "Stable"
            directionCorrect = 1 if direction == actualDirection else 0

    # Update the prediction row to indicate that it's been scored.
    cursor.execute(f"""
        UPDATE {tableName}
        SET actualValue = ?, errorAbs = ?, errorPct = ?, directionCorrect = ?
        WHERE id = ?
    """, (actual, errorAbs, errorPct, directionCorrect, predictionId))

# Loads the weapon history records from the rarity table.
def loadWeaponHistoryRecords(cursor, rarityTable: str, itemName: str) -> list[dict]:
    """Map DB rows to predictor records: item / date / value (/ demand)."""
    cursor.execute(f"""
        SELECT name, createdAt, value, demand
        FROM {rarityTable}
        WHERE name = ?
        ORDER BY createdAt ASC
    """, (itemName,))
    records = []
    for name, createdAt, value, demand in cursor.fetchall():
        records.append({
            "item": name,
            "date": createdAt,
            "value": value,
            "demand": demand,
        })
    return records

def listWeaponNames(cursor, rarityTable: str) -> list[str]:
    cursor.execute(f"SELECT DISTINCT name FROM {rarityTable} ORDER BY name")
    return [row[0] for row in cursor.fetchall() if row[0]]
