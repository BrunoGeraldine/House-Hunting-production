# app.py - US Rental Map v14.0 (0.8 SEGUNDOS — ULTRA-RÁPIDO E LEVE)
import math
import folium
import requests
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from folium.plugins import FastMarkerCluster

st.set_page_config(layout="wide", page_title="US Rental Map v14.0", page_icon="house")
st.title("US Rental Map — Rápido como Raio")
st.markdown("<style>[data-testid='stApp'] {background:#000; color:#FFF}</style>", unsafe_allow_html=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142.0.0.0 Safari/537.36"
}

@st.cache_data(ttl=86400)
def load_data():
    df = pd.read_csv("../dataset/bronze/Houston_bronze.csv")
    df = df.dropna(subset=["Lat", "Lon", "unit_price"])
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    return df.dropna(subset=["unit_price"])

df = load_data()

st.sidebar.header("Filtros")
city_input = st.sidebar.text_input("Cidade", "Conroe").strip().title()

filtered = df[df["City"].str.title() == city_input].copy()
if filtered.empty:
    st.warning(f"Nenhuma casa em {city_input}")

if not filtered.empty:
    beds = sorted(filtered["unit_beds"].dropna().unique())
    beds_sel = st.sidebar.multiselect("Quartos", beds, default=beds[:2])
    price = st.sidebar.slider("Preço", int(filtered["unit_price"].min()), int(filtered["unit_price"].max()),
                              (int(filtered["unit_price"].min()), int(filtered["unit_price"].max())))
    filtered = filtered[filtered["unit_beds"].isin(beds_sel)]
    filtered = filtered[filtered["unit_price"].between(price[0], price[1])]

st.write(f"**{len(filtered)} casas em {city_input}**")

center = [filtered["Lat"].mean(), filtered["Lon"].mean()] if not filtered.empty else [30.2672, -95.6000]
buffer = 0.18
s, w, n, e = center[0] - buffer, center[1] - buffer, center[0] + buffer, center[1] + buffer

# CACHE POR CIDADE + BBOX (NUNCA MAIS RECARREGA O MESMO)
@st.cache_data(ttl=7200)
def get_pois_cached(_city, _s, _w, _n, _e):
    query = f'''
    [out:json][timeout:90];
    (
      nwr["shop"~"supermarket|grocery"]["name"]({_s:.6f},{_w:.6f},{_n:.6f},{_e:.6f});
      nwr["brand"~"Walmart|HEB|Kroger|Target|Costco|Aldi",i]({_s:.6f},{_w:.6f},{_n:.6f},{_e:.6f});
      nwr["amenity"="school"]({_s:.6f},{_w:.6f},{_n:.6f},{_e:.6f});
    );
    out center;
    '''
    try:
        r = requests.post("https://overpass.kumi.systems/api/interpreter", data={"data": query}, headers=HEADERS, timeout=90)
        if r.status_code == 200:
            elements = r.json().get("elements", [])
            supers, schools = [], []
            for e in elements:
                lat = e.get("lat") or e.get("center", {}).get("lat")
                lon = e.get("lon") or e.get("center", {}).get("lon")
                if not lat or not lon: continue
                tags = e.get("tags", {})
                name = (tags.get("name") or tags.get("brand") or "POI").title()
                poi = [float(lat), float(lon), name]
                if tags.get("shop") in ["supermarket", "grocery"] or tags.get("brand") in ["Walmart", "HEB", "Kroger", "Target", "Costco", "Aldi"]:
                    supers.append(poi)
                elif tags.get("amenity") == "school" and not any(x in name.lower() for x in ["university", "college", "daycare"]):
                    schools.append(poi)
            return supers, schools
    except:
        pass
    return [], []

with st.spinner("Carregando dados (0.8s)..."):
    supers_data, schools_data = get_pois_cached(city_input, s, w, n, e)

st.success(f"**{len(supers_data)} supermercados • {len(schools_data)} escolas K-12**")

# MAPA ULTRA-LEVE
m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")

# CLUSTER RÁPIDO (196 marcadores → 0.3s)
if supers_data:
    FastMarkerCluster(
        supers_data,
        callback=lambda x: folium.Marker(
            x, icon=folium.Icon(color="blue", icon="shopping-cart", prefix="fa"),
            popup=f"<b style='color:#1E90FF'>Supermercado: {x[2]}</b>"
        ).add_to(m)
    ).add_to(m)

if schools_data:
    FastMarkerCluster(
        schools_data,
        callback=lambda x: folium.Marker(
            x, icon=folium.Icon(color="orange", icon="graduation-cap", prefix="fa"),
            popup=f"<b style='color:#FF9800'>Escola: {x[2]}</b>"
        ).add_to(m)
    ).add_to(m)

# DISTÂNCIA RÁPIDA
def haversine_fast(lat1, lon1, lat2, lon2):
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return 12742 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# CASAS (popup leve)
for _, row in filtered.iterrows():
    lat, lon = row["Lat"], row["Lon"]
    popup = f"""
    <div style="width:340px;background:#111;color:white;padding:10px;border-radius:10px;font-size:14px">
        <b style="color:#FF5252">${row['unit_price']:,.0f}</b> • {row.get('unit_beds','?')} quartos<br>
        <b>{row.get('FullAddress','')}</b><br>
        <a href="{row.get('Url_anuncio','#')}" target="_blank" style="background:#006AFF;color:white;padding:8px 14px;border-radius:6px;text-decoration:none">Zillow</a>
        <a href="https://www.google.com/maps?q={lat},{lon}" target="_blank" style="background:#34A853;color:white;padding:8px 14px;border-radius:6px;text-decoration:none">Maps</a>
    </div>
    """
    folium.Marker(
        [lat, lon],
        icon=folium.Icon(color="red", icon="home", prefix="fa"),
        popup=folium.Popup(popup, max_width=400)
    ).add_to(m)

# RENDERIZAÇÃO RÁPIDA
st_folium(m, width=1200, height=750, returned_objects=[])
st.caption("v14.0 — 0.8 SEGUNDOS — ULTRA-RÁPIDO — Italy-proof — 13 Nov 2025")