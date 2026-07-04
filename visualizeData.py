import sqlite3
import pandas as pd

conn = sqlite3.connect("weapons.db")

df = pd.read_sql("""
    SELECT name, value, minRange, maxRange, demand, stabilityScore, createdAt
    FROM godlies
    ORDER BY createdAt
""", conn)

df["createdAt"] = pd.to_datetime(df["createdAt"])
conn.close()

print(df.head())
print(df["name"].nunique(), "items,", df["createdAt"].nunique(), "snapshots")

import matplotlib.pyplot as plt

item = "Waves"
item_df = df[df["name"] == item].sort_values("createdAt")

plt.figure(figsize=(10, 5))
plt.plot(item_df["createdAt"], item_df["value"], marker="o")
plt.title(f"{item} value over time")
plt.xlabel("Date")
plt.ylabel("Value")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("travelers_gun.png", dpi=150)