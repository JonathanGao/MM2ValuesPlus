"""
Export all weapon value rows from weapons.db to CSV.

Columns: item, date, value, demand
"""
import csv
import sqlite3
from pathlib import Path

from sqlManager import WEAPONS_DB, WEAPONS_RARITIES, EXCLUDED_GODLIES

OUTPUT_CSV = Path(__file__).resolve().parent / "weapons_export.csv"


def exportWeaponsCsv(outputPath: Path = OUTPUT_CSV) -> int:
    connection = sqlite3.connect(WEAPONS_DB)
    cursor = connection.cursor()

    rows = []
    for rarity, tableName in WEAPONS_RARITIES.items():
        cursor.execute(f"""
            SELECT name, createdAt, value, demand
            FROM {tableName}
            ORDER BY name, createdAt
        """)
        for name, createdAt, value, demand in cursor.fetchall():
            # Skip placeholder godlies (e.g. Batwing on godlies); ancients Batwing is kept
            if tableName == WEAPONS_RARITIES["godlies"] and name in EXCLUDED_GODLIES:
                continue
            date = str(createdAt).split(" ")[0] if createdAt else ""
            rows.append({
                "item": name,
                "date": date,
                "value": value,
                "demand": demand if demand is not None else "",
            })

    connection.close()

    outputPath.parent.mkdir(parents=True, exist_ok=True)
    with outputPath.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "date", "value", "demand"])
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


if __name__ == "__main__":
    count = exportWeaponsCsv()
    print(f"Wrote {count} rows to {OUTPUT_CSV}")
