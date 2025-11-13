# app.py - US Rental Map v16.0 PRO — FINAL PROFISSIONAL
import math
import folium
import requests
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from folium.plugins import FastMarkerCluster

# CONFIG
st.set_page_config(layout="wide", page_title="US Rental Map PRO", page_icon="house")
st.markdown("<h1 style='text-align:center;color:#FF5252'>'>US Rental Map PRO</h1>", unsafe_allow_html=True)
st.markdown("<style>[data-testid='stApp'] {background:#000;color:#FFF}</style>", unsafe_allow_html=True)

# ESTADOS AMERICANOS (51)
states = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA",
    "ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK",
    "OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"
]

# BARRA DE ESTADOS
cols = st.columns(len(states))
selected_state = st.session_state.get("state", "TX")
for i, state in enumerate(states):
    with cols[i]:
        if st.button(state, key=state, width="stretch"):
            selected_state = state
            st.session_state.state = state
            st.session_state.city = ""
            st.rerun()

# FILTROS
st.sidebar.header(f"Estado: **{selected_state}**")
city_input = st.sidebar.text_input("Cidade", value=st.session_state.get("city", "Conroe"), key="city_input")
beds_sel = st.sidebar.multiselect("Quartos", [1,2,3,4,5,"5+"], default=[2])
price_range = st.sidebar.slider("Preço (USD)", 500, 10000, (1000, 5000), step=100)

# CARREGA DADOS
@st.cache_data(ttl=86400)
def load_all_data():
    df = pd.read_csv("../dataset/bronze/Houston_bronze.csv")
    df = df.dropna(subset=["Lat", "Lon", "unit_price", "City"])
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df = df.dropna(subset=["unit_price"])
    df["state"] = "TX"  # Futuro: múltiplos CSVs
    return df

df = load_all_data()

# FILTRA
filtered = df[
    (df["City"].str.title() == city_input.title()) &
    (df["state"] == selected_state) &
    (df["unit_beds"].isin(beds_sel) if beds_sel else True) &
    (df["unit_price"].between(price_range[0], price_range[1]))
].copy()

# LIMITA A 50 IMÓVEIS + ORDENA POR PREÇO
if not filtered.empty:
    filtered = filtered.sort_values("unit_price").head(50)
    center = [filtered["Lat"].mean(), filtered["Lon"].mean()]
else:
    st.warning(f"Nenhum imóvel em {city_input}, {selected_state}")
    center = [30.2672, -95.6000]
    filtered = pd.DataFrame()

st.write(f"**{len(filtered)} imóveis encontrados em {city_input}, {selected_state}**")

# HAVERSINE
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# POIS DENTRO DE 5KM DOS IMÓVEIS
@st.cache_data(ttl=86400)
def get_pois_near_houses(_key, lats, lons):
    if not lats: return [], []
    query = f'''
    [out:json][timeout:60];
    (
      nwr["shop"~"supermarket|grocery"]["name"](around:5000,{",".join([f"{la},{lo}" for la,lo in zip(lats,lons)])});
      nwr["brand"~"Walmart|Best Buy|Savers|HEB|Kroger|Target|Costco|Aldi",i](around:5000,{",".join([f"{la},{lo}" for la,lo in zip(lats,lons)])});
      nwr["amenity"="school"](around:5000,{",".join([f"{la},{lo}" for la,lo in zip(lats,lons)])});
    );
    out center;
    '''
    try:
        r = requests.post("https://overpass.kumi.systems/api/interpreter", data={"data": query}, timeout=60)
        if r.status_code == 200:
            supers, schools = [], []
            for e in r.json().get("elements", []):
                lat = e.get("lat") or e.get("center", {}).get("lat")
                lon = e.get("lon") or e.get("center", {}).get("lon")
                if not lat or not lon: continue
                name = e["tags"].get("name") or e["tags"].get("brand", "POI")
                if e["tags"].get("shop") or "brand" in e["tags"]:
                    supers.append([float(lat), float(lon), name.title()])
                elif e["tags"].get("amenity") == "school":
                    if not any(x in name.lower() for x in ["university","college","daycare"]):
                        schools.append([float(lat), float(lon), name.title()])
            return supers, schools
    except:
        pass
    return [], []

lats = filtered["Lat"].tolist()
lons = filtered["Lon"].tolist()
with st.spinner("Buscando supermercados e escolas próximos (até 5km)..."):
    supers, schools = get_pois_near_houses(f"{city_input}_{selected_state}", lats, lons)

st.success(f"**{len(supers)} supermercados • {len(schools)} escolas K-12 (até 5km)**")

# MAPA
m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")

# SUPERMERCADOS
if supers:
    FastMarkerCluster(supers, callback=lambda x: folium.CircleMarker(
        location=x[:2], radius=5, color="#1E90FF", fill=True,
        popup=f"<b>Supermercado: {x[2]}</b>"
    )).add_to(m)

# ESCOLAS
if schools:
    FastMarkerCluster(schools, callback=lambda x: folium.CircleMarker(
        location=x[:2], radius=5, color="#FF9800", fill=True,
        popup=f"<b>Escola: {x[2]}</b>"
    )).add_to(m)

# IMÓVEIS
for _, row in filtered.iterrows():
    dist_sup = min([haversine(row["Lat"], row["Lon"], s[0], s[1]) for s in supers], default=999) if supers else 999
    dist_sch = min([haversine(row["Lat"], row["Lon"], s[0], s[1]) for s in schools], default=999) if schools else 999
    popup = f"""
    <div style="width:340px;background:#111;color:white;padding:12px;border-radius:12px">
        <b style="color:#FF5252">${row['unit_price']:,.0f}</b> • {row['unit_beds']} quartos<br>
        <b>{row['FullAddress']}</b><br>
        <small>Supermercado: {dist_sup:.1f}km | Escola: {dist_sch:.1f}km</small><br><br>
        <a href="{row['Url_anuncio']}" target="_blank" style="background:#006AFF;color:white;padding:10px;border-radius:6px;text-decoration:none">Zillow</a>
        <a href="https://www.google.com/maps?q={row['Lat']},{row['Lon']}" target="_blank" style="background:#34A853;color:white;padding:10px;border-radius:6px;text-decoration:none">Maps</a>
    </div>
    """
    folium.Marker(
        [row["Lat"], row["Lon"]],
        icon=folium.Icon(color="red", icon="home", prefix="fa", icon_size=(38,38)),
        popup=folium.Popup(popup, max_width=400)
    ).add_to(m)

st_folium(m, width=1200, height=550, returned_objects=[])

# TABELA FINAL
if not filtered.empty:
    result = filtered.copy()
    result["dist_sup"] = result.apply(lambda r: min([haversine(r["Lat"], r["Lon"], s[0], s[1]) for s in supers], default=999), axis=1)
    result["dist_sch"] = result.apply(lambda r: min([haversine(r["Lat"], r["Lon"], s[0], s[1]) for s in schools], default=999), axis=1)
    result = result.sort_values(by=["unit_price", "dist_sch", "dist_sup"])
    st.subheader("Ranking de Imóveis")
    st.dataframe(
        result[["FullAddress", "unit_price", "unit_beds", "dist_sch", "dist_sup", "Url_anuncio"]].rename(columns={
            "FullAddress": "Endereço",
            "unit_price": "Preço USD",
            "unit_beds": "Quartos",
            "dist_sch": "Escola (km)",
            "dist_sup": "Supermercado (km)",
            "Url_anuncio": "Link Zillow"
        }),
        use_container_width=True,
        hide_index=True
    )

st.caption("v16.0 PRO — 51 estados • 50 imóveis • 5km • Tabela com ranking • Italy-proof • 13 Nov 2025")