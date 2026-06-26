"""One-off script: normalize value/minRange/maxRange in weapons.db to numeric types."""
import sqlite3

WEAPONS_DB = "weapons.db"
TABLES = ["godlies", "chromas", "legendaries", "ancients"]

def parseNumeric(value):
    cleaned = str(value).replace(",", "").strip()
    if "." in cleaned:
        return float(cleaned)   # legendaries like 0.6
    return int(cleaned)

def normalize(value):
    if value is None:
        return None
    try:
        return parseNumeric(value)
    except (TypeError, ValueError):
        return value


def main():
    conn = sqlite3.connect(WEAPONS_DB)
    cursor = conn.cursor()

    for table in TABLES:
        cursor.execute(f"SELECT id, value, minRange, maxRange FROM {table}")
        rows = cursor.fetchall()
        updated = 0
        for row_id, value, min_range, max_range in rows:
            new_value = normalize(value)
            new_min = normalize(min_range)
            new_max = normalize(max_range)
            if (new_value, new_min, new_max) != (value, min_range, max_range):
                cursor.execute(
                    f"UPDATE {table} SET value = ?, minRange = ?, maxRange = ? WHERE id = ?",
                    (new_value, new_min, new_max, row_id),
                )
                updated += 1
        print(f"{table}: updated {updated} / {len(rows)} rows")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    main()
