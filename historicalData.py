import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3

from time import sleep
from datetime import datetime, timezone
from parseGodlies import parsePageForItems, findUpdateLog
from sqlManager import createTableWeapons, getWeaponRange, insertWeapons, createTableUpdateLog, insertUpdateLog, scrapedToday

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
    weaponsArchiveIndexes = requests.get(f"https://web.archive.org/cdx/search/cdx?url=https://supremevalues.com/mm2/{directory}/&output=json").json()
    header = weaponsArchiveIndexes[0]
    # Turn archiveIndexes into a dictionary rather than a list of lists
    weaponArchiveIndexes = [dict(zip(header, index)) for index in weaponArchiveIndexes[1:]]
    siteUrl = f"https://supremevalues.com/mm2/{directory}/"

    for index in weaponsArchiveIndexes:
        page = requests.get(f"https://web.archive.org/web/{index["timestamp"]}/{siteUrl}")
        print(f"Retrieved page {index} from {index["timestamp"]}")
        dateUsed = datetime.strptime(index["timestamp"], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)

        weapons = parsePageForItems("https://supremevalues.com/", gameRarity=gameRarity, expectedTiers=expectedTiers, html=page.text)
        weaponsRange = getWeaponRange(weapons)
        weaponsUpdateLogs = findUpdateLog("https://supremevalues.com/", html=page.text)
        insertWeapons(cursor, weapons, weaponsRange, weaponTable)
        insertUpdateLog(cursorLog, weaponsUpdateLogs, updateLogTable)

        sleep(10)

parseAndInsertPage(directory="godlies", gameRarity="godly", expectedTiers=["tier3", "tier2", "tier1", "tier0"], weaponTable=godliesTable, updateLogTable=godliesUpdateLogTable)
parseAndInsertPage(directory="chromas", gameRarity="chroma", expectedTiers=["tier3w", "tier2w", "tier1w"], weaponTable=chromasTable, updateLogTable=chromasUpdateLogTable)
parseAndInsertPage(directory="legendaries", gameRarity="legendary", expectedTiers=["tiertierspecial", "tier3", "tier2", "tier1"], weaponTable=legendariesTable, updateLogTable=legendariesUpdateLogTable)
parseAndInsertPage(directory="ancients", gameRarity="ancient", expectedTiers=["2", "1"], weaponTable=ancientsTable, updateLogTable=ancientsUpdateLogTable)

connection.commit()
connectionLog.commit()

connection.close()
connectionLog.close()
print("Disconnected from databases")