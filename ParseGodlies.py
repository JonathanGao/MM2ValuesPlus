import sys
import requests
from bs4 import BeautifulSoup
import lxml

from utils import parseForMultipleElementsOnClass, parseForSingleElementOnClass, parseForSingleElementOnId, parseTierTable

def parseGodliesPage():
    response = requests.get("https://supremevalues.com/mm2/godlies")
    if response.status_code != 200:
        print("Failed to get the response")
        sys.exit(1)

    soup = BeautifulSoup(response.text, "lxml")

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

    # Parse the tier tables for tier tables 3, 2, 1, and 0
    ExpectedTiers = [3, 2, 1, 0]
    ParsedTierTable = {}

    for tier in ExpectedTiers:
        ParsedTierTable[tier] = parseTierTable(tierTableTiers, tier)
        
    # Check that all 4 tiers are present in the ParsedTierTable
    for tier in ExpectedTiers:
        if tier not in ParsedTierTable:
            print(f"Tier {tier} is not present in the ParsedTierTable")
            sys.exit(1)

    # For every tier in the ParsedTierTable, parse the item columns
    ParsedItemColumns = {}
    FinalWeaponsList = {}

    for tier in ParsedTierTable:
        ParsedItemColumns[tier] = parseForMultipleElementsOnClass(ParsedTierTable[tier], "div", "itemcolumn")

        # Now replace the ParsedItemColumns id with the name of each weapon.
        for itemColumn in ParsedItemColumns[tier]:
            moreData = itemColumn.find("td", class_="itemimage")
            itemButton = moreData.find_all("button")
            if not itemButton:
                print("Failed to get the item button")
                sys.exit(1)
            elif len(itemButton) != 1 and len(itemButton) > 0:
                print("Multiple item buttons found")
                sys.exit(1)
            itemButton = itemButton[0]
            
            itemName = itemButton.get('data-name')
            if not itemName:
                print("Failed to get the item name")
                sys.exit(1)
            itemValue = itemColumn.get('data-value')
            if not itemValue:
                print("Failed to get the item value")
                sys.exit(1)
            itemRange = itemColumn.find('b', class_='itemrange').text
            if not itemRange:
                print("Failed to get the item range")
                sys.exit(1)
            itemDemand = itemColumn.get('data-demand')
            if not itemDemand:
                print("Failed to get the item demand")
                sys.exit(1)
            itemRarity = itemColumn.get('data-rarity')
            if not itemRarity:
                print("Failed to get the item rarity")
                sys.exit(1)
            itemStabilityScore = itemColumn.get('data-stability-score')
            if not itemStabilityScore:
                print("Failed to get the item stability score")
                sys.exit(1)
            itemFlippability = itemButton.get('data-flippability')
            if not itemFlippability:
                print("Failed to get the item flippability")
                sys.exit(1)
            itemChanceOfRising = itemButton.get('data-cor')
            if not itemChanceOfRising:
                print("Failed to get the item chance of rising")
                sys.exit(1)
            
            # Insert into FinalWeaponsList
            FinalWeaponsList[itemName] = {
                "tier": tier,
                "value": itemValue,
                "range": itemRange,
                "stability": itemStabilityScore,
                "demand": itemDemand,
                "rarity": itemRarity,
                "flippability": itemFlippability,
                "chanceOfRising": itemChanceOfRising,
            }

    return FinalWeaponsList
