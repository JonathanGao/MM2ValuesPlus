import sqlite3

from utils import formatValue

def createTableWeapons(cursor, tableName):
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {tableName} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL, -- either "supremevalues" or "mm2values"
    gameRarity TEXT NOT NULL, -- either "common", "uncommon", "rare", "legendary", "vintage", "godly", "ancient", or "chroma"
    tier INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    value INTEGER, 
    minRange INTEGER, 
    maxRange INTEGER,  
    stabilityScore INTEGER, 
    demand INTEGER, 
    rarity INTEGER, 
    flippability TEXT, 
    chanceOfRising INTEGER,
    createdAt TEXT NOT NULL default CURRENT_TIMESTAMP
);""")
    print("createTable function success")

def createTableUpdateLog(cursor, tableName):
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {tableName} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL, -- either "supremevalues" or "mm2values"
    log TEXT NOT NULL,
    createdAt TEXT default CURRENT_TIMESTAMP
);""")
    print("createTableUpdateLog function success")

def getWeaponRange(weaponsData):
    weaponRange = {}
    for i in weaponsData:
        weapon = weaponsData[i]
        # Range is a string, parse the string to separate it into the minimum and maximums of the range.
        Range = weapon["range"]
        minRange, maxRange = None, None
        if "-" in Range:
            rawParsedRange = list(map(lambda x: x.strip(), Range.split("-")))
            finalParsedRange = list(map(lambda x: formatValue(x), rawParsedRange))
            
            if finalParsedRange[0] > finalParsedRange[1]:
                minRange, maxRange = finalParsedRange[1], finalParsedRange[0]
            else:
                minRange, maxRange = finalParsedRange[0], finalParsedRange[1]
        else:
            value = formatValue(weapon["value"])
            minRange, maxRange = value, value
        weaponRange[weapon["name"]] = {
            "minRange": minRange,
            "maxRange": maxRange,
        }
    return weaponRange

def insertWeapons(cursor, weapons, weaponRange, weaponTable: str):
    for weapon in weapons:
        weaponData = weapons[weapon]
        weaponRangeMin = None
        weaponRangeMax = None
        if weaponRange[weapon]:
            weaponRangeMin, weaponRangeMax = weaponRange[weapon]["minRange"], weaponRange[weapon]["maxRange"]
        cursor.execute(f"""
        INSERT INTO {weaponTable} (name, source, gameRarity, tier, value, minRange, maxRange, stabilityScore, demand, rarity, flippability, chanceOfRising, createdAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            weaponData["name"],
            weaponData["source"],
            weaponData["gameRarity"],
            weaponData["tier"],
            weaponData["value"],
            weaponRangeMin,
            weaponRangeMax,
            weaponData["stabilityScore"],
            weaponData["demand"],
            weaponData["rarity"],
            weaponData["flippability"],
            weaponData["chanceOfRising"],
            weaponData["createdAt"],
        ))

def insertUpdateLog(cursor, updateLogs, updateLogTable: str):
    for updateLog in updateLogs:
        cursor.execute(f"""
        INSERT INTO {updateLogTable} (source, log)
        VALUES (?, ?)
        """, (
            updateLog["source"],
            updateLog["log"],
        ))
    print("insertUpdateLog function success")

def scrapedToday(cursor, tableName: str, source: str = "supremevalues") -> bool:
    cursor.execute(f"""
        SELECT 1 FROM {tableName}
        WHERE source = ? AND date(createdAt) = date('now', 'localtime')
        LIMIT 1
    """, (source,))
    return cursor.fetchone() is not None