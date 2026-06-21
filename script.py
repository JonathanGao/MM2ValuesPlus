import requests
from bs4 import BeautifulSoup
import lxml

response = requests.get("https://supremevalues.com/mm2/godlies")
print(response)

soup = BeautifulSoup(response.text, "lxml")
title = soup.title
print(title.text)

if "Blossom" in response.text:
    print("Blossom is in the response")
else:
    print("Blossom is not in the response")