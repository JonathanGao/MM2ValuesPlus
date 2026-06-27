import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3
import time

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

archiveIndexes = requests.get("https://web.archive.org/cdx/search/cdx?url=https://supremevalues.com/&output=json").json()
header = archiveIndexes[0]
# Turn archiveIndexes into a dictionary rather than a list of lists
archiveIndexes = [dict(zip(header, index)) for index in archiveIndexes[1:]]
siteUrl = "https://supremevalues.com/godlies/"

for index in archiveIndexes:
    page = requests.get(f"https://web.archive.org/web/{index["timestamp"]}/{siteUrl}")
    print(f"Retrieved page {index} from {index["timestamp"]}")
    time.sleep(10)
    dateUsed = datetime.strptime(index["timestamp"], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)

    godlies = parsePageForItems("https://supremevalues.com/", gameRarity="godly", expectedTiers=["tier3", "tier2", "tier1", "tier0"], html=page.text)
    godlyRange = getWeaponRange(godlies)
    insertWeapons(cursor, godlies, godlyRange, godliesTable)
    godliesUpdateLogs = findUpdateLog("https://supremevalues.com/mm2/godlies")
    insertUpdateLog(cursorLog, godliesUpdateLogs, godliesUpdateLogTable)

connection.close()
connectionLog.close()
print("Disconnected from databases")