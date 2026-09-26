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

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

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

def _shortDate(isoDate: str) -> str:
    # Turn a stored day like "2026-09-26" into the short label shown next to
    # each value in the sidebar, such as "Sep 26". Month names are fixed here
    # so the label does not change with the computer's language setting.
    year, month, day = isoDate.split("-")
    return f"{_MONTHS[int(month) - 1]} {int(day)}"

def _dailyDates(cursor, table: str) -> list[str]:
    # Daily scrapes are the rows that include demand. Value-history backfill
    # rows leave demand empty, so they are left out. Newest day comes first.
    return [
        row[0]
        for row in cursor.execute(
            f"""
            SELECT DISTINCT date(createdAt)
            FROM {table}
            WHERE demand IS NOT NULL
            ORDER BY 1 DESC
            """
        ).fetchall()
    ]

def listActualScrapeDates() -> list[str]:
    # Every UTC day that has at least one daily scrape, in any rarity.
    # The calendar uses this list to decide which days can be clicked.
    # Oldest day is first.
    connection = sqlite3.connect(WEAPONS_DB)
    cursor = connection.cursor()
    dates = set()
    for table in WEAPONS_RARITIES.values():
        dates.update(_dailyDates(cursor, table))
    connection.close()
    return sorted(dates)

def getActualTopMovers(limit: int = 5, onDate: str | None = None):
    """
    Build the Actual top-movers list.

    Each weapon is compared across two daily scrapes. onDate is the later of
    those two days, written as YYYY-MM-DD. Leave it empty to use the latest
    scrape for each rarity and the scrape before that.

    If at least one value changed, the list is the biggest percent moves.
    If nothing changed, the list is the highest values, each shown as
    old value -> same value and 0%, so the sidebar is not left blank.
    """
    connection = sqlite3.connect(WEAPONS_DB)
    cursor = connection.cursor()
    paired = []
    sawScrape = False
    sawPrevious = False

    for rarity, table in WEAPONS_RARITIES.items():
        dates = _dailyDates(cursor, table)
        # A chosen day only counts for this rarity when that rarity was
        # actually scraped then. The earlier day is the closest scrape
        # before it, which may be more than one calendar day back.
        if onDate:
            if onDate not in dates:
                continue
            sawScrape = True
            earlier = [day for day in dates if day < onDate]
            if not earlier:
                continue
            sawPrevious = True
            latestDate, previousDate = onDate, earlier[0]
        else:
            if len(dates) < 2:
                if dates:
                    sawScrape = True
                continue
            sawScrape = True
            sawPrevious = True
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
            if changePct is None:
                continue
            paired.append(
                _formatMover(
                    rarity,
                    name,
                    previousValue,
                    currentValue,
                    changePct,
                    fromDate=previousDate,
                    toDate=latestDate,
                    fromDateLabel=_shortDate(previousDate),
                    toDateLabel=_shortDate(latestDate),
                )
            )

    connection.close()

    # Nothing could be compared. Tell the page whether the chosen day has
    # no scrape at all, or a scrape with no older day to measure against.
    if not paired:
        if onDate and not sawScrape:
            status = "no-scrape"
        else:
            status = "no-previous"
        return {"movers": [], "flat": False, "status": status}

    # Keep real moves when any value changed. Otherwise fill the list with
    # the most expensive items so a flat day still shows 3000 -> 3000, 0%.
    changed = [mover for mover in paired if mover["changePct"] != 0]
    if changed:
        changed.sort(key=lambda mover: abs(mover["changePct"]), reverse=True)
        chosen = changed[:limit]
        flat = False
    else:
        paired.sort(key=lambda mover: (-mover["currentValue"], mover["name"]))
        chosen = paired[:limit]
        flat = True

    return {"movers": chosen, "flat": flat, "status": "ok"}

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
