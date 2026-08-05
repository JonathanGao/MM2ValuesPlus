import sqlite3
import pandas as pd
from sqlManager import WEAPONS_RARITIES, WEAPONS_DB, EXCLUDED_GODLIES
from utils import displayErrorMessage



def getWeaponJson(rarity, weaponName, app):
    if weaponName in EXCLUDED_GODLIES:
        return displayErrorMessage(f"Weapon {weaponName} is excluded from the analysis.", app)
    connection = sqlite3.connect(WEAPONS_DB)
    df = pd.read_sql_query(f'SELECT * FROM {WEAPONS_RARITIES[rarity]} WHERE name = "{weaponName}";', connection)
    if df.empty:
        return displayErrorMessage(f"Weapon {weaponName} does not exist.", app)
    return df.to_json(orient="records")