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

connection = sqlite3.connect(weaponsDb)
cursor = connection.cursor()

connectionLog = sqlite3.connect(updateLogDb)
cursorLog = connectionLog.cursor()

createTableUpdateLog(cursorLog, godliesUpdateLogTable)
createTableUpdateLog(cursorLog, chromasUpdateLogTable)
createTableUpdateLog(cursorLog, legendariesUpdateLogTable)
createTableUpdateLog(cursorLog, ancientsUpdateLogTable)

createTableWeapons(cursor, godliesTable)
createTableWeapons(cursor, chromasTable)
createTableWeapons(cursor, legendariesTable)
createTableWeapons(cursor, ancientsTable)

def parseAndInsertPage(directory: str, gameRarity: str, expectedTiers: list[str], weaponTable: str, updateLogTable: str):
    print(f"=== Starting to parse and insert page for {directory} ===")
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

    for index in weaponsArchiveIndexes:
        dateUsed = datetime.strptime(index["timestamp"], "%Y%m%d%H%M%S")

        scraped = scrapedOnDate(cursor, weaponTable, dateUsed)
        scrapedLog = scrapedOnDate(cursorLog, updateLogTable, dateUsed)
        if scraped and scrapedLog:
            print(f"Skipping {dateUsed} because it already exists in the database and the update log")
            continue
        
        page = requests.get(f"https://web.archive.org/web/{index["timestamp"]}id_/{siteUrl}", timeout=100)
        print(f"Retrieved page {index} from {index["timestamp"]}")
        if len(page.text) < 5000 or "main-wrapper" not in page.text:
            print(f"Skipping bad snapshot {index['timestamp']} (length {len(page.text)})")
            continue
        

        # The functions need dateUsed to be passed in to make it a value for the createdAt key in the dictionary
        if not scraped:
            weapons = parsePageForItems("https://supremevalues.com/", gameRarity=gameRarity, expectedTiers=expectedTiers, dateUsed=dateUsed, html=page.text)
            weaponsRange = getWeaponRange(weapons)
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
        if not scrapedLog:
            weaponsUpdateLogs = findUpdateLog("https://supremevalues.com/", date=dateUsed, html=page.text)
            insertUpdateLog(cursorLog, weaponsUpdateLogs, updateLogTable)
            connectionLog.commit()

        sleep(10)
    print(f"=== Finished parsing and inserting page for {directory} ===")
    sleep(10)

parseAndInsertPage(directory="godlies", gameRarity="godly", expectedTiers=["tier3", "tier2", "tier1", "tier0"], weaponTable=godliesTable, updateLogTable=godliesUpdateLogTable)
parseAndInsertPage(directory="chromas", gameRarity="chroma", expectedTiers=["tier3w", "tier2w", "tier1w"], weaponTable=chromasTable, updateLogTable=chromasUpdateLogTable)
parseAndInsertPage(directory="legendaries", gameRarity="legendary", expectedTiers=["tiertierspecial", "tier3", "tier2", "tier1"], weaponTable=legendariesTable, updateLogTable=legendariesUpdateLogTable)
parseAndInsertPage(directory="ancients", gameRarity="ancient", expectedTiers=["2", "1"], weaponTable=ancientsTable, updateLogTable=ancientsUpdateLogTable)

print("Disconnected from databases")