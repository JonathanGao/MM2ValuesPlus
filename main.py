import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3

from parseGodlies import parseWeaponsPage, findUpdateLog
from sqlManager import createTableWeapons, getGodlyRange, insertWeapons, createTableUpdateLog, insertUpdateLog

godliesDb = "godlies.db"
godliesTable = "godlies"

updateLogDb = "updateLog.db"
updateLogTable = "updateLog"

connection = sqlite3.connect(godliesDb)
cursor = connection.cursor()

connectionLog = sqlite3.connect(updateLogDb)
cursorLog = connectionLog.cursor()


def main():
    createTableUpdateLog(cursorLog, updateLogTable)
    createTableWeapons(cursor, godliesTable)

    godlies = parseWeaponsPage("https://supremevalues.com/mm2/godlies")
    godliesUpdateLogs = findUpdateLog("https://supremevalues.com/mm2/godlies")

    # Gets the ranges only for the weapons with a range.
    godlyRange = getGodlyRange(godlies)
    print(f"Found range for {len(godlyRange)} godlies")

    # Insert the godly update logs into the database
    insertUpdateLog(cursorLog, godliesUpdateLogs, updateLogTable)

    # insert all godlies into database, making sure to not overwrite existing data
    insertWeapons(cursor, godlies, godlyRange, godliesTable)

    connection.commit()
    connectionLog.commit()
    connection.close()
    connectionLog.close()
    print("disconnected from databases")
main()