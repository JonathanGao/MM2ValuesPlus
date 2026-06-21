import sys
import requests
from bs4 import BeautifulSoup
import lxml

from ParseGodlies import parseGodliesPage

def main():
    godlies = parseGodliesPage()
    print(godlies["Traveler's Gun"])

main()