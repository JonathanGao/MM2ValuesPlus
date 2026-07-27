# Pull historical supremevalues.com MM2 pages from the Wayback Machine
# and insert weapon values + update logs into local SQLite DBs.
import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3
import pandas as pd

from time import sleep
from datetime import datetime, timezone
from parseGodlies import parsePageForItems, findUpdateLog
from sqlManager import createTableWeapons, getWeaponRange, insertWeapons, createTableUpdateLog, insertUpdateLog, scrapedToday, scrapedOnDate

# --- DB file names and table names ---
weaponsDb = "weapons.db"
godliesTable = "godlies"
godliesUpdateLogTable = "GodliesUpdateLog"
godliesTable = "godlies"
chromasTable = "chromas"
ancientsTable = "ancients"
legendariesTable = "legendaries"
updateLogDb = "updateLog.db"
godliesUpdateLogTable = "GodliesUpdateLog"
chromasUpdateLogTable = "ChromasUpdateLog"
legendariesUpdateLogTable = "LegendariesUpdateLog"
ancientsUpdateLogTable = "AncientsUpdateLog"

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

def parseAndInsertPage(directory: str, gameRarity: str, expectedTiers: list[str], weaponTable: str, updateLogTable: str):
    """Fetch every Wayback snapshot for one rarity page, parse it, and insert into DBs."""
    print(f"=== Starting to parse and insert page for {directory} ===")

    # CDX API: list of all archived snapshots for this page
    try:
        weaponsArchiveIndexes = requests.get(f"https://web.archive.org/cdx/search/cdx?url=https://supremevalues.com/mm2/{directory}/&output=json", timeout=100).json()
    except Exception as e:
        print(f"Failed to get the weapons archive indexes for {directory}")
        print(e)
        return
    header = weaponsArchiveIndexes[0]
    # Turn archiveIndexes into a dictionary rather than a list of lists
    weaponsArchiveIndexes = [dict(zip(header, index)) for index in weaponsArchiveIndexes[1:]]
    siteUrl = f"https://supremevalues.com/mm2/{directory}/"

    # Process each archived snapshot in chronological order
    for index in weaponsArchiveIndexes:
        dateUsed = datetime.strptime(index["timestamp"], "%Y%m%d%H%M%S")

        # Skip if this timestamp is already stored in both DBs
        scraped = scrapedOnDate(cursor, weaponTable, dateUsed)
        scrapedLog = scrapedOnDate(cursorLog, updateLogTable, dateUsed)
        if scraped and scrapedLog:
            print(f"Skipping {dateUsed} because it already exists in the database and the update log")
            continue
        
        # Download the raw HTML snapshot (id_ = original page, no Wayback toolbar)
        page = requests.get(f"https://web.archive.org/web/{index["timestamp"]}id_/{siteUrl}", timeout=100)
        print(f"Retrieved page {index} from {index["timestamp"]}")

        # Reject empty/error placeholders from Archive.org
        if len(page.text) < 5000 or "main-wrapper" not in page.text:
            print(f"Skipping bad snapshot {index['timestamp']} (length {len(page.text)})")
            continue
        

        # Parse weapons from HTML and insert if not already in weapons.db
        # The functions need dateUsed to be passed in to make it a value for the createdAt key in the dictionary
        if not scraped:
            weapons = parsePageForItems("https://supremevalues.com/", gameRarity=gameRarity, expectedTiers=expectedTiers, dateUsed=dateUsed, html=page.text)
            weaponsRange = getWeaponRange(weapons)
            # Preview rows for debugging
            rows = []
            for i in weapons:
                weapon = weapons[i]
                r = weaponsRange[weapon["name"]]
                rows.append({
                    "name": weapon["name"],
                    "tier": weapon["tier"],
                    "value": weapon["value"],
                    "minRange": r["minRange"],
                    "maxRange": r["maxRange"],
                    "createdAt": weapon["createdAt"],
                })
            df = pd.DataFrame(rows)
            print(df.head())
            print(df["createdAt"].unique())
            insertWeapons(cursor, weapons, weaponsRange, weaponTable)
            connection.commit()

        # Parse the page's update log and insert if not already in updateLog.db
        if not scrapedLog:
            weaponsUpdateLogs = findUpdateLog("https://supremevalues.com/", date=dateUsed, html=page.text)
            insertUpdateLog(cursorLog, weaponsUpdateLogs, updateLogTable)
            connectionLog.commit()

        # Pause between snapshots to reduce Archive.org rate limiting
        sleep(10)
    print(f"=== Finished parsing and inserting page for {directory} ===")
    sleep(10)

# --- Run for each rarity page ---
parseAndInsertPage(directory="godlies", gameRarity="godly", expectedTiers=["tier3", "tier2", "tier1", "tier0"], weaponTable=godliesTable, updateLogTable=godliesUpdateLogTable)
parseAndInsertPage(directory="chromas", gameRarity="chroma", expectedTiers=["tier3w", "tier2w", "tier1w"], weaponTable=chromasTable, updateLogTable=chromasUpdateLogTable)
parseAndInsertPage(directory="legendaries", gameRarity="legendary", expectedTiers=["tiertierspecial", "tier3", "tier2", "tier1"], weaponTable=legendariesTable, updateLogTable=legendariesUpdateLogTable)
parseAndInsertPage(directory="ancients", gameRarity="ancient", expectedTiers=["2", "1"], weaponTable=ancientsTable, updateLogTable=ancientsUpdateLogTable)

# --- Clean up ---
connection.close()
connectionLog.close()
print("Disconnected from databases")
