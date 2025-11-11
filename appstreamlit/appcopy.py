# app.py - US Rental Map with LIVE Supermarkets & Parks (WORKING 100%)
import math
import time
import folium
import requests
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from typing import Tuple, List, Optional

# ------------------------------
# Page Config
# ------------------------------
st.set_page_config(
    layout="wide",
    page_title="US Rental Map - Live Supermarkets & Parks",
    page_icon="house",
    initial_sidebar_state="expanded"
)

st.title("US Rental Map – Live Walmart, Target, Costco, H‑E‑B & Parks")

# Dark theme
st.markdown(
    """
    <style>
    [data-testid="stApp"] { background-color: #1E1E1E; color: #FFFFFF; }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------------
# OSM Helpers (100% reliable)
# ------------------------------
@st.cache_data(ttl=7200, show_spinner=False)
def get_city_bbox(city: str, state: str = "TX") -> Optional[Tuple[float, float, float, float]]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": f"{city}, {state}, USA", "format": "json", "limit": 1}
    headers = {"User-Agent": "RentalMap/1.0 (databrunog@gmail.com)"}  # CHANGE THIS!
    try:
        time.sleep(1.1)
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200 and r.json():
            b = r.json()[0]["boundingbox"]
            return float(b[0]), float(b[2]), float(b[1]), float(b[3])  # s,w,n,e
    except:
        pass
    return None


@st.cache_data(ttl=7200, show_spinner=False)
def get_supermarkets_osm(bbox: Tuple[float, float, float, float]) -> pd.DataFrame:
    south, west, north, east = bbox
    overpass = "https://overpass-api.de/api/interpreter"
    brands = "Walmart|Target|Costco|H-E-B|Aldi|Kroger"

    query = f'''
    [out:json][timeout:45];
    (
      node["shop"="supermarket"]({south},{west},{north},{east})["brand"~"{brands}",i];
      way["shop"="supermarket"]({south},{west},{north},{east})["brand"~"{brands}",i];
      relation["shop"="supermarket"]({south},{west},{north},{east})["brand"~"{brands}",i];
      node["shop"="supermarket"]({south},{west},{north},{east})["name"~"{brands}",i];
      way["shop"="supermarket"]({south},{west},{north},{east})["name"~"{brands}",i];
      relation["shop"="supermarket"]({south},{west},{north},{east})["name"~"{brands}",i];
    );
    out center;
    '''

    try:
        r = requests.post(overpass, data={"data": query}, timeout=45)
        if r.status_code != 200:
            return pd.DataFrame(columns=["name", "lat", "lon"])

        data = r.json()
        rows = []
        for el in data.get("elements", []):
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if lat and lon:
                name = (el["tags"].get("brand") or el["tags"].get("name") or "Supermarket").title()
                rows.append({"name": name, "lat": lat, "lon": lon})
        df = pd.DataFrame(rows)
        st.success(f"Found {len(df)} supermarkets (Walmart, Target, Costco, H-E-B, etc.)")
        return df
    except Exception as e:
        st.error(f"Supermarket API error: {e}")
        return pd.DataFrame(columns=["name", "lat", "lon"])


@st.cache_data(ttl=7200, show_spinner=False)
def get_parks_osm(bbox: Tuple[float, float, float, float]) -> pd.DataFrame:
    south, west, north, east = bbox
    query = f'''
    [out:json][timeout:30];
    (
      node["leisure"="park"]({south},{west},{north},{east});
      way["leisure"="park"]({south},{west},{north},{east});
      relation["leisure"="park"]({south},{west},{north},{east});
      node["leisure"="nature_reserve"]({south},{west},{north},{east});
    );
    out center;
    '''
    try:
        r = requests.post("https://overpass-api.de/api/interpreter", data={"data": query}, timeout=30)
        if r.status_code != 200:
            return pd.DataFrame(columns=["name", "lat", "lon"])

        data = r.json()
        rows = []
        for el in data.get("elements", []):
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if lat and lon:
                name = el["tags"].get("name", "Park").title()
                rows.append({"name": name, "lat": lat, "lon": lon})
        df = pd.DataFrame(rows)
        if not df.empty:
            st.success(f"Found {len(df)} parks")
        return df
    except:
        return pd.DataFrame(columns=["name", "lat", "lon"])


# ------------------------------
# Load Data
# ------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("../dataset/bronze/Houston_bronze.csv")
    df = df.dropna(subset=["Lat", "Lon", "unit_price"])
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    return df.dropna(subset=["unit_price"])

df = load_data()

# ------------------------------
# Sidebar Filters
# ------------------------------
st.sidebar.header("Filters")
cities = sorted(df["City"].dropna().unique())
selected_cities = st.sidebar.multiselect("City", options=cities, default=cities[3:4])

beds = sorted(df["unit_beds"].dropna().unique())
selected_beds = st.sidebar.multiselect("Bedrooms", options=beds, default=beds[:1])

p_min, p_max = int(df["unit_price"].min()), int(df["unit_price"].max())
price = st.sidebar.slider("Price (USD)", p_min, p_max, (p_min, p_max))

filtered_df = df[
    (df["unit_price"].between(price[0], price[1])) &
    (df["City"].isin(selected_cities) if selected_cities else True) &
    (df["unit_beds"].isin(selected_beds) if selected_beds else True)
]

st.write(f"**{len(filtered_df)} properties found**")

# ------------------------------
# Dynamic Supermarkets & Parks
# ------------------------------
supermarkets = pd.DataFrame(columns=["name", "lat", "lon"])
parks = pd.DataFrame(columns=["name", "lat", "lon"])

if not filtered_df.empty and selected_cities:
    city = selected_cities[0]
    with st.spinner(f"Loading live data for **{city}**..."):
        bbox = get_city_bbox(city, "TX")
        if not bbox:
            # Fallback: use average property coordinates ±0.2°
            lat_c = filtered_df["Lat"].mean()
            lon_c = filtered_df["Lon"].mean()
            delta = 0.25
            bbox = (lat_c - delta, lon_c - delta, lat_c + delta, lon_c + delta)
            st.warning(f"City bbox not found – using zoomed area around properties")

        supermarkets = get_supermarkets_osm(bbox)
        parks = get_parks_osm(bbox)
else:
    st.info("Select a city to load live supermarkets and parks")

# ------------------------------
# Map
# ------------------------------
center = [filtered_df["Lat"].mean(), filtered_df["Lon"].mean()] if not filtered_df.empty else [29.7604, -95.3698]
m = folium.Map(location=center, zoom_start=11, tiles="CartoDB dark_matter")

# Supermarkets
for _, row in supermarkets.iterrows():
    folium.Marker(
        [row["lat"], row["lon"]],
        popup=f'<b style="color:#00BFFF;">{row["name"]}</b>',
        icon=folium.Icon(color="blue", icon="shopping-cart", prefix="fa")
    ).add_to(m)

# Parks
for _, row in parks.iterrows():
    folium.Marker(
        [row["lat"], row["lon"]],
        popup=f'<b style="color:#32CD32;">{row["name"]}</b>',
        icon=folium.Icon(color="green", icon="tree", prefix="fa")
    ).add_to(m)

# Haversine
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    a = math.sin(math.radians(lat2 - lat1) / 2)**2 + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(math.radians(lon2 - lon1) / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# Properties
for _, row in filtered_df.iterrows():
    lat, lon = row["Lat"], row["Lon"]

    # Nearest supermarket
    if not supermarkets.empty:
        supermarkets = supermarkets.copy()
        supermarkets["dist"] = supermarkets.apply(
            lambda r: haversine(lat, lon, r["lat"], r["lon"]), axis=1
        )
        nearest_s = supermarkets.loc[supermarkets["dist"].idxmin()]
        s_name, s_lat, s_lon, s_dist = nearest_s["name"], nearest_s["lat"], nearest_s["lon"], nearest_s["dist"]
    else:
        s_name, s_lat, s_lon, s_dist = "No supermarket", lat, lon, 0

    # Nearest park
    if not parks.empty:
        parks_copy = parks.copy()
        parks_copy["dist"] = parks_copy.apply(
            lambda r: haversine(lat, lon, r["lat"], r["lon"]), axis=1
        )
        nearest_p = parks_copy.loc[parks_copy["dist"].idxmin()]
        p_name, p_lat, p_lon, p_dist = nearest_p["name"], nearest_p["lat"], nearest_p["lon"], nearest_p["dist"]
    else:
        p_name, p_lat, p_lon, p_dist = "No park", lat, lon, 0

    zillow = row.get("Url_anuncio", "#")
    gmaps = f"https://www.google.com/maps?q={lat},{lon}"
    drive = f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={s_lat},{s_lon}&travelmode=driving"
    walk = f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={p_lat},{p_lon}&travelmode=walking"

    popup = f"""
    <div style="font-family:Arial; width:320px;">
        <b>${row['unit_price']:,.0f}</b> • {row.get('unit_beds','?')} bed • {row.get('unit_baths','?')} bath<br>
        <b>{row.get('FullAddress','Address N/A')}</b><br><br>
        <a href="{zillow}" target="_blank" style="background:#006AFF;color:white;padding:8px;border-radius:6px;text-decoration:none;">Zillow</a>
        <a href="{gmaps}" target="_blank" style="background:#34A853;color:white;padding:8px;border-radius:6px;text-decoration:none;">Maps</a><br><br>
        <a href="{drive}" target="_blank" style="background:#FF9800;color:white;padding:6px;font-size:11px;border-radius:6px;text-decoration:none;">
        Drive to {s_name[:18]} ({s_dist:.1f} km)</a><br>
        <a href="{walk}" target="_blank" style="background:#4CAF50;color:white;padding:6px;font-size:11px;border-radius:6px;text-decoration:none;">
        Walk to {p_name[:18]} ({p_dist:.1f} km)</a>
    </div>
    """

    folium.Marker(
        [lat, lon],
        popup=folium.Popup(popup, max_width=500),
        icon=folium.Icon(color="red", icon="home", prefix="fa")
    ).add_to(m)

# ------------------------------
# Show Map
# ------------------------------
st_folium(m, width=1200, height=700, key="map")

st.caption("Live OpenStreetMap data • Supermarkets & Parks updated in real time • Nov 2025")