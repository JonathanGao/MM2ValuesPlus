import sqlite3
import pandas as pd
from sqlManager import WEAPONS_RARITIES, WEAPONS_DB, EXCLUDED_GODLIES
from utils import displayErrorMessage

def checkExcluded(weaponName, rarity, app):
    if rarity == WEAPONS_RARITIES['godlies'] and weaponName in EXCLUDED_GODLIES:
        return displayErrorMessage(f"Weapon {weaponName} is excluded from the analysis.", app)
    else:
        return False

def getWeaponJson(rarity, weaponName, app):
    # Placeholder godlies (e.g. Batwing on the godlies page) are excluded only there;
    # the real ancient Batwing must still be available via /api/ancients/Batwing.
    checkExcluded(weaponName, rarity, app)
    connection = sqlite3.connect(WEAPONS_DB)
    df = pd.read_sql_query(f'SELECT * FROM {WEAPONS_RARITIES[rarity]} WHERE name = "{weaponName}";', connection)
    if df.empty:
        return displayErrorMessage(f"Weapon {weaponName} does not exist.", app)
    return df.to_json(orient="records")

def getPredictions(rarity, weaponName, app):
    checkExcluded(weaponName, rarity, app)
    connection = sqlite3.connect(WEAPONS_DB)
    df = pd.read_sql_query(f'SELECT * FROM predictions WHERE rarity = "{rarity}" AND item = "{weaponName}" ORDER BY predictedAt ASC;', connection)
    if df.empty:
        return displayErrorMessage(f"Predictions for {weaponName} do not exist.", app)
    return df.to_json(orient="records")