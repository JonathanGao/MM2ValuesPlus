import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3

from parseGodlies import parseWeaponsPage, findUpdateLog
from sqlManager import createTable, getGodlyRange, insertWeapons
godliesDb = "godlies.db"
godliesTable = "godlies"

connection = sqlite3.connect(godliesDb)
cursor = connection.cursor()

godlies = parseWeaponsPage("https://supremevalues.com/mm2/godlies")
updateLog = findUpdateLog("https://supremevalues.com/mm2/godlies")
print(updateLog)

connection.close()