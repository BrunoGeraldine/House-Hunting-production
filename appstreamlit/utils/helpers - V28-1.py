# utils/helpers.py
import requests
from config.settings import HEADERS, DEFAULT_CENTER
import streamlit as st

def get_city_center(city_name):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{city_name}, TX, USA", "format": "json", "limit": 1},
            headers=HEADERS,
            timeout=15
        )
        data = r.json()
        if data:
            b = data[0]["boundingbox"]
            lat = (float(b[0]) + float(b[1])) / 2
            lon = (float(b[2]) + float(b[3])) / 2
            return [lat, lon]
    except:
        pass
    return DEFAULT_CENTER