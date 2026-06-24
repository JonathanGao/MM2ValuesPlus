import sys

from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime, timezone

def getCurrentTimestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def getSourceFromLink(link: str):
    source = None
    hostname = (urlparse(link).hostname or "").lower()
    if "supremevalues" in hostname:
        source = "supremevalues"
    elif "mm2values" in hostname:
        source = "mm2values"
    else:
        print(f"Invalid source: {hostname}")
        sys.exit(1)
    return source

def parseForMultipleElementsOnClass(element, type : str, class_ : str):
    # Check if type is valid, if there is no specified type, use the default type of ""
    if not type:
        type = None
    elif not type in ["div", "section", "article", "span", "p", "h1", "h2", "h3", "h4", "h5", "h6", None]:
        print(f"Invalid type: {type}")
        sys.exit(1)

    if type:
        elements = element.find_all(type, class_=class_)
        if not elements:
            print(f"Failed to get the elements with class '{class_}' and type '{type}'")
            sys.exit(1)
    else:
        elements = element.find_all(class_=class_)
        if not elements:
            print(f"Failed to get the elements with class '{class_}'")
            sys.exit(1)
    return elements

def parseForSingleElementOnClass(element, type : str, class_ : str):
    # Check if type is valid, if there is no specified type, use the default type of ""
    if not type:
        type = None
    elif not type in ["div", "section", "article", "span", "p", "h1", "h2", "h3", "h4", "h5", "h6", None]:
        print(f"Invalid type: {type}")
        sys.exit(1)

    if type:
        elements = element.find_all(type, class_=class_)
        if not elements:
            print(f"Failed to get the element with class '{class_}' and type '{type}'")
            sys.exit(1)
        elif len(elements) != 1 and len(elements) > 0:
            print(f"Multiple elements with class '{class_}' and type '{type}' found")
            sys.exit(1)
    else:
        elements = element.find_all(class_=class_)
        if not elements:
            print(f"Failed to get the element with class '{class_}'")
            sys.exit(1)
    return elements[0]

def parseForSingleElementOnId(element, type : str, id : str):
    # Check if type is valid, if there is no specified type, use the default type of ""
    if not type:
        type = None
    elif not type in ["div", "section", "article", "span", "p", "h1", "h2", "h3", "h4", "h5", "h6", None]:
        print(f"Invalid type: {type}")
        sys.exit(1)

    if type:
        elements = element.find_all(type, id=id)
        if not elements:
            print(f"Failed to get the element with id '{id}' and type '{type}'")
            sys.exit(1)
        elif len(elements) != 1 and len(elements) > 0:
            print(f"Multiple elements with id '{id}' and type '{type}' found")
            sys.exit(1)
    else:
        elements = element.find_all(id=id)
        if not elements:
            print(f"Failed to get the element with id '{id}'")
            sys.exit(1)
        elif len(elements) != 1 and len(elements) > 0:
            print(f"Multiple elements with id '{id}' found")
            sys.exit(1)
    return elements[0]

def parseTierTable(tierTable, tier : int):
    # Parse the tier table for the tier tables 3, 2, 1, and 0
    tierTables = tierTable.find_all('section', class_="grid", id = f"tier{tier}")
    if not tierTables:
        print(f"Failed to get the tier {tier} table")
        sys.exit(1)
    elif len(tierTables) != 1 and len(tierTables) > 0:
        print(f"Multiple elements with class 'tier-{tier}' found")
        sys.exit(1)
    return tierTables[0]