import sqlite3

def createTable(cursor, tableName):
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
    createdAt TEXT default CURRENT_TIMESTAMP
);""")
    print("createTable function success")

def getGodlyRange(godliesData):
    godlyRange = {}
    for i in godliesData:
        godly = godliesData[i]
        # Range is a string, parse the string to separate it into the minimum and maximums of the range.
        Range = godly["range"]
        minRange, maxRange = None, None
        if Range == "N/A":
            minRange, maxRange = godly["value"], godly["value"]
        elif "-" in Range:
            rawParsedRange = list(map(lambda x: x.strip(), Range.split("-")))
            FinalParsedRange = list(map(lambda x: int(x.replace(",", "")), rawParsedRange))
            if rawParsedRange[0] > rawParsedRange[1]:
                minRange, maxRange = rawParsedRange[1], rawParsedRange[0]
            else:
                minRange, maxRange = rawParsedRange[0], rawParsedRange[1]
        else:
            print("Invalid range format")
            return None
        godlyRange[godly["name"]] = {
            "minRange": minRange,
            "maxRange": maxRange,
        }
    return godlyRange