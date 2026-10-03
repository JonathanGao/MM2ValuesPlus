import sys
from flask import Flask, render_template
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

# Playwright's default headless agent identifies itself as HeadlessChrome.
# Cloudflare answers that with a 403 challenge page instead of the real site.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

def launchBrowserPage(playwright):
    """Open a headless page that Cloudflare will serve instead of blocking."""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=BROWSER_USER_AGENT,
        viewport={"width": 1366, "height": 768},
        locale="en-US",
    )
    return browser, context.new_page()

def fetchPage(link: str) -> str:
    with sync_playwright() as p:
        browser, page = launchBrowserPage(p)
        try:
            response = page.goto(link, wait_until="domcontentloaded", timeout=90_000)
            # The first response can be the Cloudflare check. Wait until that
            # title is gone before treating the status as a failure.
            if response and response.status != 200:
                try:
                    page.wait_for_function(
                        """() => {
                            const title = document.title || '';
                            return !title.includes('Cloudflare') && !title.includes('Just a moment');
                        }""",
                        timeout=20_000,
                    )
                except Exception:
                    print(f"Failed to get the response with status code {response.status}")
                    sys.exit(1)
            return page.content()
        finally:
            browser.close()

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
            print(f"Failed to get the element with class '{class_}' and type '{type}' for link {element}")
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

def parseTierTable(tierTable, tier : int or str):
    # Parse the tier table for the tier tables 3, 2, 1, and 0
    tierTables = tierTable.find_all('section', class_="grid", id = f"{tier}")
    if not tierTables:
        print(f"Tier {tier} does not exist")
        return None
    elif len(tierTables) != 1 and len(tierTables) > 0:
        print(f"Multiple elements with class 'tier-{tier}' found")
        sys.exit(1)
    return tierTables[0]

def formatValue(value: str):

    text = str(value.strip().replace(",", ""))

    if text.upper().endswith("K"):
        number = float(text[:-1]) * 1000
    elif text.upper().endswith("M"):
        number = float(text[:-1]) * 1000000
    elif "." in text:
        return float(text)
    else:
        return int(text)
    return int(number) if number == int(number) else number

def displayErrorMessage(errorMessage: str, app: Flask):
    return render_template("error.html", errorMessage=errorMessage)