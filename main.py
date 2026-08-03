import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3

from parseGodlies import parsePageForItems, findUpdateLog
from sqlManager import createTableWeapons, getWeaponRange, insertWeapons, createTableUpdateLog, insertUpdateLog, scrapedToday, WEAPONS_RARITIES

weaponsDb = "weapons.db"
godliesTable = WEAPONS_RARITIES['godlies']
chromasTable = WEAPONS_RARITIES['chromas']
ancientsTable = WEAPONS_RARITIES['ancients']
legendariesTable = WEAPONS_RARITIES['legendaries']

updateLogDb = "updateLog.db"
godliesUpdateLogTable = "GodliesUpdateLog"
chromasUpdateLogTable = "ChromasUpdateLog"
ancientsUpdateLogTable = "AncientsUpdateLog"
legendariesUpdateLogTable = "LegendariesUpdateLog"

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


def main():
    anyInserted = False


    if not scrapedToday(cursor, godliesTable):
        godlies = parsePageForItems("https://supremevalues.com/mm2/godlies", gameRarity="godly", expectedTiers=["tier3", "tier2", "tier1", "tier0"])
        godlyRange = getWeaponRange(godlies)
        insertWeapons(cursor, godlies, godlyRange, godliesTable)
        anyInserted = True
    else:
        print("Godlies already scraped today, skipping")
    if not scrapedToday(cursorLog, godliesUpdateLogTable):
        godliesUpdateLogs = findUpdateLog("https://supremevalues.com/mm2/godlies")
        insertUpdateLog(cursorLog, godliesUpdateLogs, godliesUpdateLogTable)
        anyInserted = True
    else:
        print("Godlies update log already scraped today, skipping")

    if not scrapedToday(cursor, chromasTable):
        chromas = parsePageForItems("https://supremevalues.com/mm2/chromas", gameRarity="chroma", expectedTiers=["tier3w", "tier2w", "tier1w"])
        chromasRange = getWeaponRange(chromas)
        insertWeapons(cursor, chromas, chromasRange, chromasTable)
        anyInserted = True
    else:
        print("Chromas already scraped today, skipping")
    if not scrapedToday(cursorLog, chromasUpdateLogTable):
        chromasUpdateLogs = findUpdateLog("https://supremevalues.com/mm2/chromas")
        insertUpdateLog(cursorLog, chromasUpdateLogs, chromasUpdateLogTable)
        anyInserted = True
    else:
        print("Chromas update log already scraped today, skipping")

    if not scrapedToday(cursor, legendariesTable):
        legendaries = parsePageForItems("https://supremevalues.com/mm2/legendaries", gameRarity="legendary", expectedTiers=["tiertierspecial", "tier3", "tier2", "tier1"])
        legendariesRange = getWeaponRange(legendaries)
        insertWeapons(cursor, legendaries, legendariesRange, legendariesTable)
        anyInserted = True
    else:
        print("Legendaries already scraped today, skipping")
    if not scrapedToday(cursorLog, legendariesUpdateLogTable):
        legendariesUpdateLogs = findUpdateLog("https://supremevalues.com/mm2/legendaries")
        insertUpdateLog(cursorLog, legendariesUpdateLogs, legendariesUpdateLogTable)
        anyInserted = True
    else:
        print("Legendaries update log already scraped today, skipping")

    if not scrapedToday(cursor, ancientsTable):
        ancients = parsePageForItems("https://supremevalues.com/mm2/ancients", gameRarity="ancient", expectedTiers=["2", "1"])
        ancientsRange = getWeaponRange(ancients)
        insertWeapons(cursor, ancients, ancientsRange, ancientsTable)
        anyInserted = True
    else:
        print("Ancients already scraped today, skipping")
    if not scrapedToday(cursorLog, ancientsUpdateLogTable):
        ancientsUpdateLogs = findUpdateLog("https://supremevalues.com/mm2/ancients")
        insertUpdateLog(cursorLog, ancientsUpdateLogs, ancientsUpdateLogTable)
        anyInserted = True
    else:
        print("Ancients update log already scraped today, skipping")

    
    if anyInserted == True:
        connection.commit()
        connectionLog.commit()
        print("Committed new data to databases")
    else:
        print("Nothing new to commit — today's data already exists")
    connection.close()
    connectionLog.close()
    print("Disconnected from databases")


main()