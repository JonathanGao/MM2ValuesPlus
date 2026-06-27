import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3

from datetime import datetime, timezone, date, time
from parseGodlies import parsePageForItems, findUpdateLog
from sqlManager import createTableWeapons, createTableUpdateLog, getWeaponRange, insertWeapons, insertUpdateLog
godliesDb = "godlies.db"
godliesTable = "godlies"
chromasTable = "chromas"
ancientsTable = "ancients"
legendariesTable = "legendaries"
updateLogDb = "updateLog.db"
godliesUpdateLogTable = "GodliesUpdateLog"
chromasUpdateLogTable = "ChromasUpdateLog"
legendariesUpdateLogTable = "LegendariesUpdateLog"
ancientsUpdateLogTable = "AncientsUpdateLog"

connection = sqlite3.connect(godliesDb)
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

cursor.execute("UPDATE legendaries SET chanceOfRising = NULL WHERE chanceOfRising = 'N/A';")

# godlies = parsePageForItems("https://supremevalues.com/mm2/godlies")
# updateLogs = findUpdateLog("https://supremevalues.com/mm2/godlies")
# insertUpdateLog(cursorLog, updateLogs, updateLogTable)

# chromas = parsePageForItems("https://supremevalues.com/mm2/chromas", gameRarity="chroma", expectedTiers=["tier3w", "tier2w", "tier1w"])
# chromasUpdateLogs = findUpdateLog("https://supremevalues.com/mm2/chromas")
# chromasRange = getWeaponRange(chromas)
# insertWeapons(cursor, chromas, chromasRange, chromasTable)
# insertUpdateLog(cursorLog, chromasUpdateLogs, chromasUpdateLogTable)

# legendaries = parsePageForItems("https://supremevalues.com/mm2/legendaries", gameRarity="legendary", expectedTiers=["tiertierspecial", "tier3", "tier2", "tier1"])
# legendariesUpdateLogs = findUpdateLog("https://supremevalues.com/mm2/legendaries")
# legendariesRange = getWeaponRange(legendaries)
# insertWeapons(cursor, legendaries, legendariesRange, legendariesTable)
# insertUpdateLog(cursorLog, legendariesUpdateLogs, legendariesUpdateLogTable)

# ancients = parsePageForItems("https://supremevalues.com/mm2/ancients", gameRarity="ancient", expectedTiers=["2", "1"])
# ancientsUpdateLogs = findUpdateLog("https://supremevalues.com/mm2/ancients")
# ancientsRange = getWeaponRange(ancients)
# insertWeapons(cursor, ancients, ancientsRange, ancientsTable)
# insertUpdateLog(cursorLog, ancientsUpdateLogs, ancientsUpdateLogTable)

# connectionLog.commit()
connection.commit()

connection.close()
connectionLog.close()