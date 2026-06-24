import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3

from parseGodlies import parseWeaponsPage, findUpdateLog
from sqlManager import createTableWeapons, createTableUpdateLog, getGodlyRange, insertWeapons, insertUpdateLog
godliesDb = "godlies.db"
godliesTable = "godlies"
updateLogDb = "updateLog.db"
updateLogTable = "updateLog"


connection = sqlite3.connect(godliesDb)
cursor = connection.cursor()

connectionLog = sqlite3.connect(updateLogDb)
cursorLog = connectionLog.cursor()

createTableUpdateLog(cursorLog, updateLogTable)


godlies = parseWeaponsPage("https://supremevalues.com/mm2/godlies")
updateLogs = findUpdateLog("https://supremevalues.com/mm2/godlies")
insertUpdateLog(cursorLog, updateLogs, updateLogTable)

connectionLog.commit()

connection.close()
connectionLog.close()