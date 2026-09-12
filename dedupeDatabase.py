import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3

from parseGodlies import parsePageForItems, findUpdateLog
from sqlManager import createTableWeapons, getWeaponRange, insertWeapons, createTableUpdateLog, insertUpdateLog, scrapedToday, WEAPONS_DB, UPDATE_LOG_DB

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

connection = sqlite3.connect(weaponsDb)
cursor = connection.cursor()

connectionLog = sqlite3.connect(updateLogDb)
cursorLog = connectionLog.cursor()

def dedupeTable(cursor, tableName, groupCategory = "name"):
    cursor.execute(f"""
    DELETE FROM {tableName}
    WHERE id NOT IN (
    SELECT MAX(id)
    FROM {tableName}
    GROUP BY {groupCategory}, date(createdAt)
    );
    """)
    print(f"Deduped {tableName} table")

dedupeTable(cursor, godliesTable, "name")
dedupeTable(cursor, chromasTable, "name")
dedupeTable(cursor, legendariesTable, "name")
dedupeTable(cursor, ancientsTable, "name")

dedupeTable(cursorLog, godliesUpdateLogTable, "log")
dedupeTable(cursorLog, chromasUpdateLogTable, "log")
dedupeTable(cursorLog, legendariesUpdateLogTable, "log")
dedupeTable(cursorLog, ancientsUpdateLogTable, "log")

connection.commit()
connectionLog.commit()
print("Committed deduplicated data to databases")
connection.close()
connectionLog.close()
print("Disconnected from databases")