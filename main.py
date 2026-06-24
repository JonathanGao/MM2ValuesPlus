import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3

from parseGodlies import parseWeaponsPage, findChangeLog
from sqlManager import createTable, getGodlyRange, insertWeapons
godliesDb = "godlies.db"
godliesTable = "godlies"

def main():
    connection = sqlite3.connect(godliesDb)
    cursor = connection.cursor()
    createTable(cursor, godliesTable)

    godlies = parseWeaponsPage("https://supremevalues.com/mm2/godlies")

    # Gets the ranges only for the weapons with a range.
    godlyRange = getGodlyRange(godlies)
    print(f"Found range for {len(godlyRange)} godlies")

    # insert all godlies into database, making sure to not overwrite existing data
    insertWeapons(cursor, godlies, godlyRange, godliesTable)

    connection.commit()
    connection.close()
    print("disconnected from database")
main()