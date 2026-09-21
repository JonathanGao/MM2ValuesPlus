import sys
import requests
from bs4 import BeautifulSoup
import lxml
from typing import Optional
from datetime import datetime, timezone, date, time
from utils import parseForMultipleElementsOnClass, parseForSingleElementOnClass, parseForSingleElementOnId, parseTierTable, getSourceFromLink, getCurrentTimestamp, fetchPage
from playwright.sync_api import sync_playwright



# Optional date is used to filter the godlies by the date they were added. This is used to get historical data from the archive and use the date that it was archived at.
def parsePageForItems(link: str, gameRarity: str, expectedTiers: list[str], dateUsed: Optional[datetime] = None, html: Optional[str] = None):

    if not dateUsed:
        dateUsed = getCurrentTimestamp()



    source = getSourceFromLink(link)

    if not html:
        # Use a user agent to avoid being blocked by the server
        html =fetchPage(link)
        soup = BeautifulSoup(html, "lxml")
    else:
        soup = BeautifulSoup(html, "lxml")

    # Get the body of the page
    body = soup.body
    if not body:
        print("Failed to get the body")
        sys.exit(1)

    # Get the main wrapper within the body
    mainWrapper = parseForSingleElementOnClass(body, "div", "main-wrapper")
    main = parseForSingleElementOnId(mainWrapper, None, "main")
    svlContent = parseForSingleElementOnClass(main, "div", "svl-content")

    # Parse sections with class 'tier-tables', which there should be two of. One is the changelog, the other contains all the divs with the godlies in tier 3, tier 2, tier 1, and tier 0.
    tierTables = svlContent.find_all('section', class_="tier-tables")
    if not tierTables:
        print("Failed to get the tier tables")
        sys.exit(1)
    elif len(tierTables) != 2 and len(tierTables) > 2:
        print("Too many elements with class 'tier-tables' found")
        sys.exit(1)
    elif len(tierTables) == 0 or len(tierTables) == 1:
        print("Too few elements with class 'tier-tables' found")
        sys.exit(1)

    # Separate the tier tables
    for tierTable in tierTables:
        if not tierTable.has_attr('id'):
            tierTableTiers = tierTable
        elif tierTable['id'] == 'changelog':
            tierTableChangelog = tierTable

    if not tierTableTiers:
        print("Failed to get the tier tables")
        sys.exit(1)
    elif not tierTableChangelog:
        print("Failed to get the changelog")
        sys.exit(1)

    # Parse the tier tables for specified tiers.
    ParsedTierTable = {}

    for tier in expectedTiers:
        expectedTier = parseTierTable(tierTableTiers, tier)
        if expectedTier:
            ParsedTierTable[tier] = expectedTier
    # For every tier in the ParsedTierTable, parse the item columns
    ParsedItemColumns = {}
    FinalWeaponsList = {}

    for tier in ParsedTierTable:
        ParsedItemColumns[tier] = parseForMultipleElementsOnClass(ParsedTierTable[tier], "div", "itemcolumn")

        # Now replace the ParsedItemColumns id with the name of each weapon. 
        for itemColumn in ParsedItemColumns[tier]:
            # Some weapons do not have a button, and therefore these variables will be N/A in the database unless they exist.
            itemName = None
            itemFlippability = None
            itemChanceOfRising = None        
            
            itemName = itemColumn.find('div', class_='itemhead').text
            itemValue = itemColumn.get('data-value')
            if not itemValue:
                print(f"Failed to get the item value for item column {itemColumn}")
                sys.exit(1)
            itemRange = itemColumn.find('b', class_='itemrange')
            if itemRange:
                itemRange = itemRange.text
            else:
                # This can be N/A because later on in the getWeaponRange function, we will check if the range is N/A and if it is, we will set the minRange and maxRange to the value. so N/A is not inserted into the database.
                itemRange = "N/A"
            itemDemand = itemColumn.get('data-demand')
            if not itemDemand:
                print(f"Failed to get the item demand for item column {itemColumn}")
                sys.exit(1)
            itemRarity = itemColumn.get('data-rarity')
            if not itemRarity:
                print(f"Failed to get the item rarity for item column {itemColumn}")
                sys.exit(1)
            itemStabilityScore = itemColumn.get('data-stability-score')
            if not itemStabilityScore:
                print(f"Failed to get the item stability score for item column {itemColumn}")
                sys.exit(1)


            moreData = itemColumn.find("td", class_="itemimage")
            if not moreData:
                print(f"Failed to get the more data for item column {itemColumn}")
                sys.exit(1)
            itemButton = moreData.find_all("button")
            if itemButton:
                itemButton = itemButton[0]
                itemName = itemButton.get('data-name')
                if not itemName:
                    print(f"Failed to get the item name for item column {itemColumn}")
                    sys.exit(1)
                itemFlippability = itemButton.get('data-flippability')
                if not itemFlippability:
                    itemFlippability = None
                itemChanceOfRising = itemButton.get('data-cor')
                if not itemChanceOfRising or itemChanceOfRising.strip().upper() in ("", "N/A"):
                    itemChanceOfRising = None
            elif len(itemButton) != 1 and len(itemButton) > 0:
                print(f"Multiple item buttons found for item column {itemName}")
                sys.exit(1)

            
            # Insert into FinalWeaponsList
            FinalWeaponsList[itemName] = {
                "name": itemName,
                "source": source,
                "gameRarity": gameRarity,
                "tier": tier,
                "value": itemValue,
                "range": itemRange,
                "stabilityScore": itemStabilityScore,
                "demand": itemDemand,
                "rarity": itemRarity,
                "flippability": itemFlippability,
                "chanceOfRising": itemChanceOfRising,
                "createdAt": dateUsed,
            }

    return FinalWeaponsList

def findUpdateLog(link: str, date: Optional[date] = None, html: Optional[str] = None):
    
    if not date:
        date = getCurrentTimestamp()

    # Get the html page from the link

    source = getSourceFromLink(link)
    if not html:
        html = fetchPage(link)
        soup = BeautifulSoup(html, "lxml")
    else:
        soup = BeautifulSoup(html, "lxml")

    # Get the update log, it's a div with id "updatelog" and it contains a lot of children that are all divs.
    finalUpdateLogs = []
    updateLog = parseForSingleElementOnId(soup, "div", "updatelog")

    # Get the children of the update log that do not have a style(not a title or anything like that)
    updateLog = updateLog.find_all(style=False, recursive=False)

    # Format html to text so it's readable
    # Append the text of each tag to the finalUpdateLog
    for tag in updateLog:
        finalUpdateLogs.append({
            "source": source,
            "log": tag.text,
            "createdAt": date,
        })
    if updateLog == []:
        finalUpdateLogs.append({
            "source": source,
            "log": "(no changes)",
            "createdAt": date,
        })
    return finalUpdateLogs