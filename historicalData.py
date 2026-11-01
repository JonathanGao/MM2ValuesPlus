# Pull historical supremevalues.com MM2 pages from the Wayback Machine
# and insert weapon values + update logs into local SQLite DBs.
#
# Additionally scrapes each weapon's live "Value History" from Supreme Values'
# per-item pages (?item=Slug) and inserts any missing (name, createdAt) points.
import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3
import pandas as pd

from time import sleep
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

from parseGodlies import parsePageForItems, findUpdateLog
from utils import BROWSER_USER_AGENT, launchBrowserPage
from sqlManager import (
    createTableWeapons,
    getWeaponRange,
    createTableUpdateLog,
    insertUpdateLog,
    getExistingWeaponTimestamps,
    getExistingUpdateLogEntries,
    insertWeaponRecords,
    WEAPONS_DB,
    UPDATE_LOG_DB,
)

# --- DB file names and table names ---
weaponsDb = WEAPONS_DB
godliesTable = "godlies"
godliesUpdateLogTable = "GodliesUpdateLog"
godliesTable = "godlies"
chromasTable = "chromas"
ancientsTable = "ancients"
legendariesTable = "legendaries"
updateLogDb = UPDATE_LOG_DB
godliesUpdateLogTable = "GodliesUpdateLog"
chromasUpdateLogTable = "ChromasUpdateLog"
legendariesUpdateLogTable = "LegendariesUpdateLog"
ancientsUpdateLogTable = "AncientsUpdateLog"

# Be polite to supremevalues / archive.org
ITEM_HISTORY_SLEEP_SEC = 0.75
LIST_PAGE_RETRIES = 3

# --- Open DB connections ---
connection = sqlite3.connect(weaponsDb)
cursor = connection.cursor()

connectionLog = sqlite3.connect(updateLogDb)
cursorLog = connectionLog.cursor()

# --- Ensure update-log tables exist ---
createTableUpdateLog(cursorLog, godliesUpdateLogTable)
createTableUpdateLog(cursorLog, chromasUpdateLogTable)
createTableUpdateLog(cursorLog, legendariesUpdateLogTable)
createTableUpdateLog(cursorLog, ancientsUpdateLogTable)

# --- Ensure weapon tables exist ---
createTableWeapons(cursor, godliesTable)
createTableWeapons(cursor, chromasTable)
createTableWeapons(cursor, legendariesTable)
createTableWeapons(cursor, ancientsTable)

def _normalizeCreatedAt(value) -> str:
    """Normalize datetime/string createdAt values for consistent duplicate checks."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def parseAndInsertPage(directory: str, gameRarity: str, expectedTiers: list[str], weaponTable: str, updateLogTable: str):
    """Fetch every Wayback snapshot for one rarity page, parse it, and insert into DBs."""
    print(f"=== Starting to parse and insert page for {directory} ===")

    # CDX API: list of all archived snapshots for this page
    try:
        weaponsArchiveIndexes = requests.get(f"https://web.archive.org/cdx/search/cdx?url=https://supremevalues.com/mm2/{directory}/&output=json", timeout=120).json()
    except Exception as e:
        print(f"Failed to get the weapons archive indexes for {directory}")
        print(e)
        return
    # Must check if length < 2 because the first row in the list is a header row. 
    if not weaponsArchiveIndexes or len(weaponsArchiveIndexes) < 2:
        print(f"No archive snapshots found for {directory}")
        return
    header = weaponsArchiveIndexes[0]
    # Turn archiveIndexes into a dictionary rather than a list of lists
    weaponsArchiveIndexes = [dict(zip(header, index)) for index in weaponsArchiveIndexes[1:]]
    siteUrl = f"https://supremevalues.com/mm2/{directory}/"

    # Row-level dedupe sets — updated as we insert so re-runs and partial runs stay safe
    existingWeapons = getExistingWeaponTimestamps(cursor, weaponTable)
    existingLogs = getExistingUpdateLogEntries(cursorLog, updateLogTable)
    print(f"  {len(existingWeapons)} existing weapon rows, {len(existingLogs)} existing update-log rows")

    # Digests that already produced empty/Incapsula shells — skip without re-downloading
    knownBadDigests: set[str] = set()
    # CDX "length" is compressed WARC size; tiny records are almost always bad captures
    minCdxLength = 5000

    # Process each archived snapshot in chronological order
    for index in weaponsArchiveIndexes:
        dateUsed = datetime.strptime(index["timestamp"], "%Y%m%d%H%M%S")
        createdAtStr = _normalizeCreatedAt(dateUsed)
        digest = index.get("digest") or ""
        try:
            cdxLength = int(index.get("length") or 0)
        except ValueError:
            cdxLength = 0

        # Fast skip when this exact archive timestamp was already ingested into both DBs
        weaponsHaveTs = any(ts == createdAtStr for _, ts in existingWeapons)
        logsHaveTs = any(ts == createdAtStr for _, ts in existingLogs)
        if weaponsHaveTs and logsHaveTs:
            print(f"Skipping {createdAtStr} because that exact archive timestamp already exists in both DBs")
            continue

        # Skip known-bad / tiny CDX records before hitting Archive.org
        if digest and digest in knownBadDigests:
            print(f"Skipping {index['timestamp']} — known-bad digest {digest}")
            continue
        if cdxLength and cdxLength < minCdxLength:
            print(f"Skipping {index['timestamp']} — CDX length {cdxLength} looks like a bad capture")
            if digest:
                knownBadDigests.add(digest)
            continue
        
        # Download the raw HTML snapshot (id_ = original page, no Wayback toolbar)
        try:
            page = requests.get(f"https://web.archive.org/web/{index["timestamp"]}id_/{siteUrl}", timeout=100)
        except Exception as e:
            print(f"Failed to download snapshot {index['timestamp']}: {e}")
            sleep(10)
            continue
        print(f"Retrieved page {index} from {index["timestamp"]}")

        # Reject empty/error placeholders from Archive.org
        if len(page.text) < 5000 or "main-wrapper" not in page.text:
            print(f"Skipping bad snapshot {index['timestamp']} (length {len(page.text)})")
            if digest:
                knownBadDigests.add(digest)
            continue
        

        # Parse weapons and insert only (name, createdAt) pairs not already in weapons.db
        try:
            weapons = parsePageForItems("https://supremevalues.com/", gameRarity=gameRarity, expectedTiers=expectedTiers, dateUsed=dateUsed, html=page.text)
            weaponsRange = getWeaponRange(weapons)
        except (Exception, SystemExit) as e:
            print(f"Skipping {index['timestamp']} — weapon parse failed: {e}")
            if digest:
                knownBadDigests.add(digest)
            sleep(2)
            continue

        newRecords = []
        for weapon in weapons.values():
            name = weapon["name"]
            createdAt = _normalizeCreatedAt(weapon["createdAt"])
            if (name, createdAt) in existingWeapons:
                continue
            r = weaponsRange[name]
            newRecords.append({
                "name": name,
                "source": weapon["source"],
                "gameRarity": weapon["gameRarity"],
                "tier": weapon["tier"],
                "value": weapon["value"],
                "minRange": r["minRange"],
                "maxRange": r["maxRange"],
                "stabilityScore": weapon["stabilityScore"],
                "demand": weapon["demand"],
                "rarity": weapon["rarity"],
                "flippability": weapon["flippability"],
                "chanceOfRising": weapon["chanceOfRising"],
                "createdAt": createdAt,
            })
            existingWeapons.add((name, createdAt))

        if newRecords:
            rows = [{
                "name": r["name"],
                "tier": r["tier"],
                "value": r["value"],
                "minRange": r["minRange"],
                "maxRange": r["maxRange"],
                "createdAt": r["createdAt"],
            } for r in newRecords]
            df = pd.DataFrame(rows)
            inserted = insertWeaponRecords(cursor, newRecords, weaponTable)
            connection.commit()
            print(f"  Inserted {inserted} weapon rows for {createdAtStr}")
        else:
            print(f"  No new weapon rows for {createdAtStr} (all already present)")

        # Parse update log and insert only (log, createdAt) pairs not already in updateLog.db
        try:
            weaponsUpdateLogs = findUpdateLog("https://supremevalues.com/", date=dateUsed, html=page.text)
        except (Exception, SystemExit) as e:
            print(f"Skipping update log for {index['timestamp']} — parse failed: {e}")
            sleep(10)
            continue

        newLogs = []
        for updateLog in weaponsUpdateLogs:
            createdAt = _normalizeCreatedAt(updateLog["createdAt"])
            key = (updateLog["log"], createdAt)
            if key in existingLogs:
                continue
            newLogs.append({
                "source": updateLog["source"],
                "log": updateLog["log"],
                "createdAt": createdAt,
            })
            existingLogs.add(key)

        if newLogs:
            insertUpdateLog(cursorLog, newLogs, updateLogTable)
            connectionLog.commit()
            print(f"  Inserted {len(newLogs)} update-log rows for {createdAtStr}")
        else:
            print(f"  No new update-log rows for {createdAtStr} (all already present)")

        # Pause between snapshots to reduce Archive.org rate limiting
        sleep(10)
    print(f"=== Finished parsing and inserting page for {directory} ===")
    sleep(10)


def _loadListPage(page, listUrl: str) -> str:
    """Load a rarity list page until the weapon cards are on the page.

    Each card button carries data-name (the display name) and data-image
    (the slug used in ?item= URLs). The list page's _svPopup object starts
    empty and is no longer the weapon catalog.
    """
    lastError = None
    for attempt in range(1, LIST_PAGE_RETRIES + 1):
        try:
            page.goto(listUrl, wait_until="domcontentloaded", timeout=90_000)
            page.wait_for_selector(".itemcolumn button[data-name][data-image]", timeout=60_000)
            return page.content()
        except Exception as e:
            lastError = e
            print(f"  List page attempt {attempt}/{LIST_PAGE_RETRIES} failed for {listUrl}: {e}")
            sleep(2)
    raise RuntimeError(f"Failed to load list page {listUrl}: {lastError}")


def _itemSlugFromImageKey(imageKey: str) -> str:
    """mm2godlies/Vampires_Gun -> Vampires_Gun (used in ?item= URLs)."""
    return (imageKey or "").rsplit("/", 1)[-1]


def _openItemPage(browser):
    """A new context for one item page.

    Opening a second page in the same context gets a Cloudflare challenge.
    A fresh context loads that weapon's _svPopup, including its history.
    """
    context = browser.new_context(
        user_agent=BROWSER_USER_AGENT,
        viewport={"width": 1366, "height": 768},
        locale="en-US",
    )
    return context, context.new_page()


def _fetchItemHistory(browser, directory: str, itemName: str, imageKey: str) -> list[dict] | None:
    """
    Open the per-item Supreme Values page and return that weapon's value history
    points: [{"v": <number>, "t": "<YYYY-MM-DD HH:MM:SS>", "c": optional bool}, ...]
    Returns [] when the site exposes history but it is empty (no chart data yet).
    """
    slug = _itemSlugFromImageKey(imageKey)
    if not slug:
        print(f"  No image slug for {itemName}; skipping history")
        return None

    itemUrl = f"https://supremevalues.com/mm2/{directory}?item={slug}"
    lastError = None
    for attempt in range(1, LIST_PAGE_RETRIES + 1):
        context, page = _openItemPage(browser)
        try:
            response = page.goto(itemUrl, wait_until="domcontentloaded", timeout=90_000)
            title = page.title() or ""
            # A challenge page has no weapon popup. Retry in another context
            # instead of waiting for history that will not appear.
            blocked = (response is None or response.status != 200) or ("Just a moment" in title) or ("Cloudflare" in title)
            if blocked:
                status = response.status if response is not None else "none"
                raise RuntimeError(f"Item page blocked (status {status})")
            page.wait_for_function(
                """(name) => {
                    const d = window._svPopup && window._svPopup[name];
                    return !!(d && Array.isArray(d.history));
                }""",
                arg=itemName,
                timeout=20_000,
            )
            history = page.evaluate(
                """(name) => {
                    const d = window._svPopup && window._svPopup[name];
                    return (d && Array.isArray(d.history)) ? d.history : null;
                }""",
                itemName,
            )
            if history is not None and len(history) == 0:
                print(f"    No history on Supreme Values for {itemName} (empty series)")
            return history
        except Exception as e:
            lastError = e
            print(f"  History attempt {attempt}/{LIST_PAGE_RETRIES} failed for {itemName}: {e}")
            sleep(2)
        finally:
            context.close()
    print(f"  Giving up on history for {itemName}: {lastError}")
    return None


def scrapeAndInsertLiveValueHistories(
    directory: str,
    gameRarity: str,
    expectedTiers: list[str],
    weaponTable: str,
):
    """
    For every weapon on a live Supreme Values rarity page, open its item page,
    read the Value History series, and insert any (name, createdAt) points not
    already in weapons.db. Missing attrs (demand, range, etc.) are left NULL;
    minRange/maxRange are set equal to the historical value.

    The weapon list comes from the cards on the rarity page. Each button's
    data-name is the display name and data-image is the ?item= slug. History
    for that weapon is read from _svPopup after its own item page loads.
    A card whose tier section is missing still uses the first expected tier.
    """
    print(f"=== Starting live value-history scrape for {directory} ===")
    listUrl = f"https://supremevalues.com/mm2/{directory}"
    existing = getExistingWeaponTimestamps(cursor, weaponTable)
    print(f"  {len(existing)} existing (name, createdAt) pairs in {weaponTable}")

    totalNew = 0
    with sync_playwright() as p:
        browser, page = launchBrowserPage(p)

        try:
            _loadListPage(page, listUrl)
        except Exception as e:
            print(f"Failed to load {listUrl}: {e}")
            browser.close()
            return

        # Names and slugs are on the cards. _svPopup on this page is empty until
        # a single weapon's item page is opened.
        catalog = page.evaluate(
            """() => {
                const items = {};
                document.querySelectorAll('.itemcolumn').forEach(col => {
                    const btn = col.querySelector('button[data-name]');
                    const head = col.querySelector('.itemhead');
                    const name = (btn && btn.dataset.name) || (head && head.textContent.trim());
                    if (!name) return;
                    const tierSection = col.closest('section.grid');
                    items[name] = {
                        imageKey: (btn && btn.dataset.image) || '',
                        tier: (tierSection && tierSection.id) || null,
                    };
                });
                return items;
            }"""
        )

        names = sorted(catalog.keys())
        missingTier = [n for n in names if not catalog[n].get("tier")]
        print(f"  Found {len(names)} weapons on {directory} from item cards")
        if missingTier:
            print(f"  Warning: {len(missingTier)} popup items have no DOM tier (using fallback '{expectedTiers[0] if expectedTiers else 'unknown'}'): {', '.join(missingTier)}")

        fallbackTier = expectedTiers[0] if expectedTiers else "unknown"

        for i, name in enumerate(names, start=1):
            meta = catalog[name]
            imageKey = meta.get("imageKey") or ""
            tier = meta.get("tier") or fallbackTier
            print(f"  [{i}/{len(names)}] {name}")

            history = _fetchItemHistory(browser, directory, name, imageKey)
            sleep(ITEM_HISTORY_SLEEP_SEC)
            if not history:
                continue

            newRecords = []
            for point in history:
                value = point.get("v")
                createdAt = point.get("t")
                if value is None or not createdAt:
                    continue
                if (name, createdAt) in existing:
                    continue
                newRecords.append({
                    "name": name,
                    "source": "supremevalues",
                    "gameRarity": gameRarity,
                    "tier": tier,
                    "value": value,
                    # History only publishes the point value, not a trade range
                    "minRange": value,
                    "maxRange": value,
                    "stabilityScore": None,
                    "demand": None,
                    "rarity": None,
                    "flippability": None,
                    "chanceOfRising": None,
                    "createdAt": createdAt,
                })
                existing.add((name, createdAt))

            if not newRecords:
                print(f"    No new history points ({len(history)} on site)")
                continue

            inserted = insertWeaponRecords(cursor, newRecords, weaponTable)
            connection.commit()
            totalNew += inserted
            print(f"    Inserted {inserted} / {len(history)} history points")

        browser.close()

    print(f"=== Finished live value-history scrape for {directory}: {totalNew} new rows ===")


def main():
    # --- Wayback archive pass for each rarity page ---
    parseAndInsertPage(directory="godlies", gameRarity="godly", expectedTiers=["tier4", "tier3", "tier2", "tier1", "tier0"], weaponTable=godliesTable, updateLogTable=godliesUpdateLogTable)
    parseAndInsertPage(directory="chromas", gameRarity="chroma", expectedTiers=["tier3w", "tier2w", "tier1w"], weaponTable=chromasTable, updateLogTable=chromasUpdateLogTable)
    parseAndInsertPage(directory="legendaries", gameRarity="legendary", expectedTiers=["tiertierspecial", "tier3", "tier2", "tier1"], weaponTable=legendariesTable, updateLogTable=legendariesUpdateLogTable)
    parseAndInsertPage(directory="ancients", gameRarity="ancient", expectedTiers=["2", "1"], weaponTable=ancientsTable, updateLogTable=ancientsUpdateLogTable)

    # --- Live Supreme Values value-history pass (fills gaps Wayback never captured) ---
    scrapeAndInsertLiveValueHistories(directory="godlies", gameRarity="godly", expectedTiers=["tier4", "tier3", "tier2", "tier1", "tier0"], weaponTable=godliesTable)
    scrapeAndInsertLiveValueHistories(directory="chromas", gameRarity="chroma", expectedTiers=["tier3w", "tier2w", "tier1w"], weaponTable=chromasTable)
    scrapeAndInsertLiveValueHistories(directory="legendaries", gameRarity="legendary", expectedTiers=["tiertierspecial", "tier3", "tier2", "tier1"], weaponTable=legendariesTable)
    scrapeAndInsertLiveValueHistories(directory="ancients", gameRarity="ancient", expectedTiers=["2", "1"], weaponTable=ancientsTable)

    # --- Clean up ---
    connection.close()
    connectionLog.close()
    print("Disconnected from databases")


if __name__ == "__main__":
    main()
