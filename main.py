import sys
import requests
from bs4 import BeautifulSoup
import lxml
import sqlite3

from parseGodlies import parseWeaponsPage
from sqlManager import createTable, getGodlyRange

def main():
    connection = sqlite3.connect("godlies.db")
    cursor = connection.cursor()
    createTable(cursor, "godlies")

    godlies = parseWeaponsPage("https://supremevalues.com/mm2/godlies")
    print(godlies)

    # Gets the ranges only for the weapons with a range.
    godlyRange = getGodlyRange(godlies)
    print(godlyRange)

    # insert all godlies into database, making sure to not overwrite existing data
    for godly in godlies:
        godlyData = godlies[godly]
        godlyRangeMin = None
        godlyRangeMax = None
        if godlyRange[godly]:
            godlyRangeMin, godlyRangeMax = godlyRange[godly]["minRange"], godlyRange[godly]["maxRange"]
        cursor.execute("""
        INSERT INTO godlies (name, source, gameRarity, tier, value, minRange, maxRange, stabilityScore, demand, rarity, flippability, chanceOfRising)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            godlyData["name"],
            godlyData["source"],
            godlyData["gameRarity"],
            godlyData["tier"],
            godlyData["value"],
            godlyRangeMin,
            godlyRangeMax,
            godlyData["stabilityScore"],
            godlyData["demand"],
            godlyData["rarity"],
            godlyData["flippability"],
            godlyData["chanceOfRising"],
        ))

    connection.commit()
    connection.close()
    print("disconnected from database")
main()