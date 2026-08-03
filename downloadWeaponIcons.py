"""
Download weapon icons from supremevalues.com into static/weaponIcons/.

Filenames match the weapon name stored in weapons.db (e.g. "Vampire's Gun.webp").
Skips any weapon that already has a real icon file. Safe to run daily.
"""
import hashlib
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from sqlManager import WEAPONS_RARITIES

weaponsDb = "weapons.db"
iconsDir = Path("static/weaponIcons")

# Placeholder "N/A" image used when supremevalues has no real icon yet
# (seen for Chroma Sands / Chroma Icecream / Chroma Beachy — identical file).
NA_ICON_SHA256 = "df636a1c676b2d366bb826d352b41330b5212319385abf0824066b132a439884"
DOWNLOAD_RETRIES = 3

# Map DB table / rarity key → live supremevalues page
RARITY_PAGES = {
    "godlies": "https://supremevalues.com/mm2/godlies",
    "chromas": "https://supremevalues.com/mm2/chromas",
    "legendaries": "https://supremevalues.com/mm2/legendaries",
    "ancients": "https://supremevalues.com/mm2/ancients",
}


def isNaIcon(content: bytes) -> bool:
    """True if content is the shared N/A placeholder image."""
    return hashlib.sha256(content).hexdigest() == NA_ICON_SHA256


def iconExists(name: str) -> bool:
    """True if this weapon already has a real (non-N/A) .webp icon on disk."""
    path = iconsDir / f"{name}.webp"
    if not path.is_file():
        return False
    if isNaIcon(path.read_bytes()):
        return False
    return True


def getWeaponNamesFromDb(connection: sqlite3.Connection) -> set[str]:
    names = set()
    for table in WEAPONS_RARITIES.values():
        rows = connection.execute(f"SELECT DISTINCT name FROM {table}").fetchall()
        names.update(row[0] for row in rows if row[0])
    return names


def fetchPageHtml(page, pageUrl: str, retries: int = 3) -> str:
    """
    Load a rarity page and wait until item columns exist.
    supremevalues often returns an empty shell on first paint.
    """
    lastError = None
    for attempt in range(1, retries + 1):
        try:
            page.goto(pageUrl, wait_until="domcontentloaded", timeout=90_000)
            page.wait_for_selector(".itemcolumn", timeout=60_000)
            return page.content()
        except Exception as e:
            lastError = e
            print(f"  Attempt {attempt}/{retries} failed for {pageUrl}: {e}")
            time.sleep(2)
    raise RuntimeError(f"Failed to load {pageUrl} after {retries} attempts: {lastError}")


def scrapeIconsFromHtml(pageUrl: str, html: str) -> dict[str, str]:
    """Return {weaponName: absoluteImageUrl} for one rarity page."""
    soup = BeautifulSoup(html, "lxml")
    icons = {}

    for itemColumn in soup.select(".itemcolumn"):
        name = None
        button = itemColumn.select_one("td.itemimage button, button")
        if button and button.get("data-name"):
            name = button.get("data-name").strip()
        if not name:
            head = itemColumn.select_one(".itemhead")
            if head:
                name = head.get_text(strip=True)
        if not name:
            continue

        img = itemColumn.select_one("td.itemimage img, img.itemimage, img")
        if not img:
            print(f"No image found for {name} on {pageUrl}")
            continue

        src = img.get("src") or img.get("data-src")
        if not src:
            print(f"No image src for {name} on {pageUrl}")
            continue

        icons[name] = urljoin(pageUrl, src)

    return icons


def fetchImageBytes(imageUrl: str) -> bytes | None:
    response = requests.get(
        imageUrl,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=60,
    )
    if response.status_code != 200:
        print(f"  HTTP {response.status_code} ({imageUrl})")
        return None

    contentType = response.headers.get("Content-Type", "")
    # Some broken media URLs return HTML with HTTP 200
    if "image" not in contentType and not response.content.startswith((b"\x89PNG", b"RIFF", b"\xff\xd8")):
        print(f"  Not an image ({contentType}) ({imageUrl})")
        return None

    return response.content


def downloadIcon(name: str, imageUrl: str) -> bool:
    """
    Download imageUrl to iconsDir/{name}.webp.
    Retries if the response is the N/A placeholder icon.
    Returns True only when a real icon is saved.
    """
    dest = iconsDir / f"{name}.webp"

    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        content = fetchImageBytes(imageUrl)
        if content is None:
            print(f"Failed to download {name} (attempt {attempt}/{DOWNLOAD_RETRIES})")
            time.sleep(1)
            continue

        if isNaIcon(content):
            print(
                f"Got N/A placeholder for {name} "
                f"(attempt {attempt}/{DOWNLOAD_RETRIES}), checking again..."
            )
            time.sleep(1)
            continue

        dest.write_bytes(content)
        print(f"Saved {dest.name}")
        return True

    # Don't leave a stale N/A file sitting around as if it were valid
    if dest.is_file() and isNaIcon(dest.read_bytes()):
        dest.unlink()
        print(f"Removed N/A placeholder for {name}")

    print(f"Failed to download a real icon for {name} after {DOWNLOAD_RETRIES} attempts")
    return False


def main():
    iconsDir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(weaponsDb)
    dbNames = getWeaponNamesFromDb(connection)
    connection.close()
    print(f"Found {len(dbNames)} distinct weapons in database")

    # Only scrape pages if at least one DB weapon still needs a real icon
    needed = {name for name in dbNames if not iconExists(name)}
    if not needed:
        print("All weapons already have icons — nothing to do")
        return 0

    print(f"{len(needed)} weapons still need icons")

    scrapedIcons: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for rarity, pageUrl in RARITY_PAGES.items():
            print(f"Scraping icons from {pageUrl}")
            try:
                html = fetchPageHtml(page, pageUrl)
            except Exception as e:
                print(f"  Skipping {rarity}: {e}")
                continue
            pageIcons = scrapeIconsFromHtml(pageUrl, html)
            print(f"  {len(pageIcons)} icons found for {rarity}")
            scrapedIcons.update(pageIcons)
        browser.close()

    downloaded = 0
    skipped = 0
    missing = []
    failed = []

    for name in sorted(dbNames):
        if iconExists(name):
            skipped += 1
            continue

        imageUrl = scrapedIcons.get(name)
        if not imageUrl:
            missing.append(name)
            continue

        if downloadIcon(name, imageUrl):
            downloaded += 1
        else:
            failed.append(name)

    print(
        f"Done. downloaded={downloaded}, already_existed={skipped}, "
        f"no_icon_on_site={len(missing)}, failed_download={len(failed)}"
    )
    if missing:
        print("Weapons in DB with no matching icon on supremevalues:")
        for name in missing:
            print(f"  - {name}")
    if failed:
        print("Weapons whose icon URL could not be downloaded:")
        for name in failed:
            print(f"  - {name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
