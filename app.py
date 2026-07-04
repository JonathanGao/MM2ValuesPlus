import os
import sqlite3

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


st.set_page_config(layout="wide")

st.title("MM2 Values Plus")

st.write("This is a tool to help you track the values of your weapons in the game Murder Mystery 2.")

st.image(os.path.join(os.getcwd(), "static", "MM2Logo"))

st.divider()

connection = sqlite3.connect("weapons.db")
cursor = connection.cursor()

df = pd.read_sql("SELECT * FROM godlies", connection)
uniqueNames = df["name"].unique()

selectedWeapon = st.selectbox("Select a weapon", uniqueNames)

weaponData = df[df["name"] == selectedWeapon]
weaponData = weaponData.sort_values(by="createdAt", ascending=True)
weaponData["createdAt"] = pd.to_datetime(weaponData["createdAt"]).dt.strftime("%Y-%m-%d")

st.dataframe(weaponData)
st.line_chart(weaponData, x="createdAt", y="value", height=500)



connection.close()