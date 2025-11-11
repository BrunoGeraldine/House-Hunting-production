# app.py - US Rental Map v13 (ITALY-PROOF + SIDE-BY-SIDE ROUTE BUTTONS)
import math
import time
import folium
import requests
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# ==================== PAGE CONFIG ====================
st.set_page_config(layout="wide", page_title="US Rental Map PRO", page_icon="house")
st.title("US Rental Map – Homes Near Supermarkets & Schools")
st.markdown("<style>[data-testid='stApp'] {background:#000; color:#FFF}</style>", unsafe_allow_html=True)

# ==================== YOUR EXACT USER-AGENT (Chrome 142 - Italy) ====================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://your-app.streamlit.app/"
}

# ==================== LOAD PROPERTIES ====================
@st.cache_data(ttl=86400)
def load_data():
    df = pd.read_csv("../dataset/bronze/Houston_bronze.csv").dropna(subset=["Lat", "Lon", "unit_price"])
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    return df.dropna(subset=["unit_price"])

df = load_data()

# ==================== SIDEBAR ====================
st.sidebar.header("Search")
city_input = st.sidebar.text_input("Type any city", "Spring").strip().title()
cities = df["City"].dropna().unique()
city_in_dataset = city_input in cities

if city_in_dataset:
    beds = sorted(df[df["City"] == city_input]["unit_beds"].unique())
    beds_sel = st.sidebar.multiselect("Bedrooms", beds, beds[:1] if len(beds) > 0 else [])
    price_range = df[df["City"] == city_input]["unit_price"]
    price = st.sidebar.slider("Price (USD)", int(price_range.min()), int(price_range.max()),
                              (int(price_range.min()), int(price_range.max())))
else:
    st.sidebar.warning(f"{city_input} → live map only (no homes in dataset)")
    beds_sel, price = [], (0, 999999)

filtered = (df[(df["City"] == city_input) &
               (df["unit_beds"].isin(beds_sel) if beds_sel else True) &
               df["unit_price"].between(price[0], price[1])]
            if city_in_dataset else pd.DataFrame())

st.write(f"**{len(filtered)} homes in {city_input}**")

# ==================== CENTER + BBOX ====================
center = filtered[["Lat", "Lon"]].mean().values if not filtered.empty else None
if center is None:
    time.sleep(1)
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{city_input}, TX, USA", "format": "json", "limit": 1},
            headers=HEADERS,
            timeout=15
        )
        data = r.json()
        if data:
            b = data[0]["boundingbox"]
            center = [(float(b[0]) + float(b[1])) / 2, (float(b[2]) + float(b[3])) / 2]
        else:
            center = [29.7604, -95.3698]
    except:
        center = [29.7604, -95.3698]

buffer = 0.05
s, w, n, e = center[0] - buffer, center[1] - buffer, center[0] + buffer, center[1] + buffer

# ==================== ROBUST OSM QUERY ====================
@st.cache_data(ttl=1800, show_spinner="Loading live data...")
def get_osm_data(tag, value):
    query = f'''
    [out:json][timeout:60];
    (
      node[{tag}="{value}"]({s:.6f},{w:.6f},{n:.6f},{e:.6f});
      way[{tag}="{value}"]({s:.6f},{w:.6f},{n:.6f},{e:.6f});
    );
    out center;
    '''
    for attempt in range(3):
        try:
            time.sleep(2)
            response = requests.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                headers=HEADERS,
                timeout=70
            )
            if response.status_code == 200:
                try:
                    return response.json().get("elements", [])
                except:
                    continue
        except:
            time.sleep(3)
    st.warning("Overpass temporarily down. Using cache.")
    return []

supermarkets_raw = get_osm_data("shop", "supermarket")
schools_raw = get_osm_data("amenity", "school")

def process_osm(elements, default_name, exclude=None):
    exclude = exclude or ["university", "college"]
    rows = []
    for e in elements:
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lon = e.get("lon") or e.get("center", {}).get("lon")
        if not lat or not lon:
            continue
        name = e["tags"].get("name", default_name).title()
        if any(word in name.lower() for word in exclude):
            continue
        rows.append({"name": name, "lat": float(lat), "lon": float(lon)})
    return pd.DataFrame(rows)

supermarkets = process_osm(supermarkets_raw, "Supermarket")
schools = process_osm(schools_raw, "School")

st.success(f"Loaded {len(supermarkets)} supermarkets & {len(schools)} schools")

# ==================== MAP ====================
m = folium.Map(location=center, zoom_start=12,
               tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
folium.TileLayer("cartodbpositron").add_to(m)

# Supermarkets & Schools
for df, color, icon in [(supermarkets, "#1E90FF", "shopping-cart"), (schools, "#FF9800", "book")]:
    for _, r in df.iterrows():
        folium.CircleMarker(
            [r["lat"], r["lon"]], radius=6, color=color, fill=True, fill_opacity=0.9,
            popup=f"<b style='color:{color}'>{r['name']}</b>"
        ).add_to(m)

# Haversine
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    a = math.sin(math.radians(lat2 - lat1) / 2)**2 + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(math.radians(lon2 - lon1) / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# Homes with SIDE-BY-SIDE ROUTE BUTTONS
for _, row in filtered.iterrows():
    lat, lon = row["Lat"], row["Lon"]

    # Nearest supermarket
    s_near = min(supermarkets.iterrows(), key=lambda x: haversine(lat, lon, x[1]["lat"], x[1]["lon"]),
                 default=(0, {"name": "No store", "lat": lat, "lon": lon}))
    s_name, s_lat, s_lon, s_dist = s_near[1]["name"], s_near[1]["lat"], s_near[1]["lon"], \
                                   haversine(lat, lon, s_near[1]["lat"], s_near[1]["lon"])

    # Nearest school
    sc_near = min(schools.iterrows(), key=lambda x: haversine(lat, lon, x[1]["lat"], x[1]["lon"]),
                  default=(0, {"name": "No school", "lat": lat, "lon": lon}))
    sc_name, sc_lat, sc_lon, sc_dist = sc_near[1]["name"], sc_near[1]["lat"], sc_near[1]["lon"], \
                                       haversine(lat, lon, sc_near[1]["lat"], sc_near[1]["lon"])

    zillow = row.get("Url_anuncio", "#")
    gmaps = f"https://www.google.com/maps?q={lat},{lon}"
    drive_url = f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={s_lat},{s_lon}&travelmode=driving"
    walk_url = f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={sc_lat},{sc_lon}&travelmode=walking"

    popup = f"""
    <div style="width:360px;background:#111;color:white;padding:10px;border-radius:12px;font-family:Arial">
        <b style="font-size:18px;color:#FF5252">${row['unit_price']:,.0f}</b> • {row.get('unit_beds','?')} bed<br>
        <b style="color:#FFF">{row.get('FullAddress','Address N/A')}</b><br><br>

        <a href="{zillow}" target="_blank" style="background:#006AFF;color:white;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:bold;margin:4px">Zillow</a>
        <a href="{gmaps}" target="_blank" style="background:#34A853;color:white;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:bold;margin:4px">Maps</a><br><br>

        <div style="margin-top:8px;">
            <a href="{drive_url}" target="_blank" 
               style="display:block; background:#FF9800; color:white; padding:5px 8px; border-radius:6px; text-decoration:none; font-weight:bold; text-align:center; margin-bottom:4px;">
                Drive to {s_name[:24]} ({s_dist:.1f}km)
            </a>

            <a href="{walk_url}" target="_blank" 
               style="display:block; background:#9C27B0; color:white; padding:5px 8px; border-radius:6px; text-decoration:none; font-weight:bold; text-align:center;">
                Walk to {sc_name[:24]} ({sc_dist:.1f}km)
            </a>
        </div><br>
    </div>
    </div>
    """

    folium.Marker(
        [lat, lon],
        popup=folium.Popup(popup, max_width=500),
        icon=folium.Icon(color="red", icon="home", prefix="fa", icon_color="white")
    ).add_to(m)

# ==================== DISPLAY ====================
st_folium(m, width=1200, height=750)
st.caption("Italy-proof • Your Chrome 142 • Side-by-side route buttons • Live OSM • Nov 2025")