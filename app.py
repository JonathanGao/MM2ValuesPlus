import sqlite3
import pandas as pd

from flask import Flask, render_template, request
from sqlManager import WEAPONS_RARITIES, EXCLUDED_GODLIES, WEAPONS_DB
from utils import displayErrorMessage

import analysis
import predictor1


app = Flask(__name__)

rarities = [rarity for rarity in WEAPONS_RARITIES.keys()]
weaponsDb = WEAPONS_DB
excludedGodlies = EXCLUDED_GODLIES

# Make the global variable rarities accessible to all templates
@app.context_processor
def inject_rarities():
    return dict(rarities=rarities)

@app.route("/")
def index():
    return render_template("index.html", rarities=rarities)

@app.route("/<rarity>")
def rarityPage(rarity):
    if rarity not in rarities:
        return displayErrorMessage(f"Rarity {rarity} does not exist. Please choose from {", ".join(rarities)}.", app)
    
    connection = sqlite3.connect(weaponsDb)
    df = pd.read_sql_query(f"SELECT * FROM {WEAPONS_RARITIES[rarity]};", connection)
    df = df.sort_values(by="createdAt", ascending=False)
    weapons = df.drop_duplicates(subset=["name"], keep="first").sort_values(by="value", ascending=False).to_dict(orient="records")
    if rarity == WEAPONS_RARITIES['godlies']:
        excluded = excludedGodlies
    else:
        excluded = []

    return render_template("rarity.html", rarity=rarity, weapons=weapons, excluded=excluded, scripts="rarity.js")

@app.route("/api/<rarity>/<weaponName>")
def api(rarity, weaponName):
    weaponJson = analysis.getWeaponJson(rarity, weaponName, app)
    return weaponJson