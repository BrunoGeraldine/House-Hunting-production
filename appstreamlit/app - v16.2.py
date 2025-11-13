# app.py - US Rental Map v16.2 PRO — EXATAMENTE COMO VOCÊ MANDOU
import math
import folium
import requests
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from folium.plugins import FastMarkerCluster

# CONFIG
st.set_page_config(layout="wide", page_title="US Rental Map PRO", page_icon="house")
st.markdown("<h1 style='text-align:center;color:#FF5252'>US RENTAL MAP PRO</h1>", unsafe_allow_html=True)
st.markdown("<style>[data-testid='stApp'] {background:#000;color:#FFF}</style>", unsafe_allow_html=True)

# === 1. CARREGA DADOS ===
@st.cache_data(ttl=86400)
def load_data():
    df = pd.read_csv("../dataset/bronze/Houston_bronze.csv")
    df = df.dropna(subset=["Lat", "Lon", "unit_price", "City", "State"])
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df = df.dropna(subset=["unit_price"])
    return df

df_original = load_data()

# === 2. BARRA DE ESTADOS (do CSV) ===
available_states = sorted(df_original["State"].unique())
if "state" not in st.session_state:
    st.session_state.state = available_states[0] if available_states else "TX"

cols = st.columns(len(available_states))
for i, state in enumerate(available_states):
    with cols[i]:
        if st.button(state, key=state, use_container_width=True):
            st.session_state.state = state
            st.session_state.city = ""
            st.rerun()

# === 3. FILTROS NO SIDEBAR ===
st.sidebar.header(f"Estado: **{st.session_state.state}**")
city_input = st.sidebar.text_input("Cidade", value="", placeholder="Digite a cidade...", key="city")

beds_options = sorted(df_original["unit_beds"].dropna().unique())
beds_sel = st.sidebar.multiselect("Quartos", beds_options, default=beds_options[:2] if len(beds_options) >= 2 else beds_options)

price_min = int(df_original["unit_price"].min())
price_max = int(df_original["unit_price"].max())
price_range = st.sidebar.slider("Preço (USD)", price_min, price_max, (price_min, price_max + 1000))

# === 4. APLICA FILTROS → df_filtrado (SÓ DEPOIS DOS FILTROS) ===
df_filtrado = df_original[
    (df_original["State"] == st.session_state.state) &
    (df_original["City"].str.title() == city_input.strip().title()) &
    (df_original["unit_beds"].isin(beds_sel)) &
    (df_original["unit_price"].between(price_range[0], price_range[1]))
].copy()

# Limita a 50 imóveis + ordena por preço
if not df_filtrado.empty:
    df_filtrado = df_filtrado.sort_values("unit_price").head(50).reset_index(drop=True)
    center_lat = df_filtrado["Lat"].mean()
    center_lon = df_filtrado["Lon"].mean()
    center = [center_lat, center_lon]
else:
    st.warning("Nenhum imóvel encontrado com os filtros aplicados.")
    center = [30.2672, -95.6000]
    df_filtrado = pd.DataFrame()

st.write(f"**{len(df_filtrado)} imóveis encontrados**")

# === 5. SÓ AGORA: BUSCA SUPERMERCADOS E ESCOLAS DENTRO DE 5KM DOS IMÓVEIS FILTRADOS ===
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

@st.cache_data(ttl=7200)
def get_pois_around_houses(_hash, lat_list, lon_list):
    if not lat_list:
        return [], []
    
    # Monta lista de coordenadas para around:5000
    points = ",".join([f"{lat},{lon}" for lat, lon in zip(lat_list, lon_list)])
    
    query = f'''
    [out:json][timeout:90];
    (
      nwr["shop"~"supermarket|grocery"]["name"](around:5000,{points});
      nwr["brand"~"Walmart|Best Buy|Savers|HEB|Kroger|Target|Costco|Aldi",i](around:5000,{points});
      nwr["amenity"="school"](around:5000,{points});
    );
    out center;
    '''
    try:
        r = requests.post("https://overpass.kumi.systems/api/interpreter", data={"data": query}, timeout=90)
        if r.status_code == 200:
            supermarkets = []
            schools = []
            for elem in r.json().get("elements", []):
                lat = elem.get("lat") or elem.get("center", {}).get("lat")
                lon = elem.get("lon") or elem.get("center", {}).get("lon")
                if not lat or not lon: continue
                name = (elem["tags"].get("name") or elem["tags"].get("brand") or "Local").title()
                if elem["tags"].get("shop") or "brand" in elem["tags"]:
                    supermarkets.append([float(lat), float(lon), name])
                elif elem["tags"].get("amenity") == "school":
                    if not any(x in name.lower() for x in ["university", "college", "daycare", "preschool"]):
                        schools.append([float(lat), float(lon), name])
            return supermarkets, schools
    except Exception as e:
        st.error(f"Erro na API OSM: {e}")
    return [], []

# Executa BUSCA SÓ DEPOIS DO df_filtrado
with st.spinner("Buscando escolas e supermercados DENTRO de 5km dos imóveis..."):
    hash_key = f"{st.session_state.state}_{city_input}_{len(df_filtrado)}"
    supers, schools = get_pois_around_houses(hash_key, df_filtrado["Lat"].tolist(), df_filtrado["Lon"].tolist())

st.success(f"**{len(supers)} supermercados • {len(schools)} escolas K-12 (até 5km dos imóveis)**")

# === 6. SÓ AGORA: CONSTRÓI O MAPA COM OS DADOS CORRETOS ===
m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")

# Supermercados (pequenos)
if supers:
    FastMarkerCluster(
        supers,
        callback=lambda x: folium.CircleMarker(
            location=x[:2],
            radius=5,
            color="#1E90FF",
            fill=True,
            fill_opacity=0.9,
            popup=f"<b>Supermercado: {x[2]}</b>"
        )
    ).add_to(m)

# Escolas (pequenos)
if schools:
    FastMarkerCluster(
        schools,
        callback=lambda x: folium.CircleMarker(
            location=x[:2],
            radius=5,
            color="#FF9800",
            fill=True,
            fill_opacity=0.9,
            popup=f"<b>Escola: {x[2]}</b>"
        )
    ).add_to(m)

# Imóveis (grandes, em destaque)
for _, row in df_filtrado.iterrows():
    # Calcula distância real para popup
    dist_sup = min([haversine(row["Lat"], row["Lon"], s[0], s[1]) for s in supers], default=99) if supers else 99
    dist_sch = min([haversine(row["Lat"], row["Lon"], s[0], s[1]) for s in schools], default=99) if schools else 99

    popup_html = f"""
    <div style="width:360px;background:#111;color:white;padding:14px;border-radius:12px;font-family:Arial">
        <b style="color:#FF5252;font-size:19px">${row['unit_price']:,.0f}</b> • {row['unit_beds']} quartos<br>
        <b style="font-size:15px">{row['FullAddress']}</b><br>
        <small>Supermercado mais próximo: {dist_sup:.1f}km<br>Escola mais próxima: {dist_sch:.1f}km</small><br><br>
        <a href="{row['Url_anuncio']}" target="_blank" style="background:#006AFF;color:white;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:bold">Zillow</a>
        <a href="https://www.google.com/maps?q={row['Lat']},{row['Lon']}" target="_blank" style="background:#34A853;color:white;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:bold">Maps</a>
    </div>
    """
    folium.Marker(
        [row["Lat"], row["Lon"]],
        icon=folium.Icon(color="red", icon="home", prefix="fa", icon_size=(42, 42)),
        popup=folium.Popup(popup_html, max_width=400)
    ).add_to(m)

# === 7. EXIBE MAPA ===
st_folium(m, width=1200, height=550, returned_objects=[])

# === 8. TABELA FINAL ===
if not df_filtrado.empty:
    tabela = df_filtrado.copy()
    tabela["dist_sup"] = tabela.apply(lambda r: min([haversine(r["Lat"], r["Lon"], s[0], s[1]) for s in supers], default=99), axis=1)
    tabela["dist_sch"] = tabela.apply(lambda r: min([haversine(r["Lat"], r["Lon"], s[0], s[1]) for s in schools], default=99), axis=1)
    tabela = tabela.sort_values(by=["unit_price", "dist_sch", "dist_sup"])

    st.subheader("Ranking Final: Preço + Proximidade")
    st.dataframe(
        tabela[["FullAddress", "unit_price", "unit_beds", "dist_sch", "dist_sup", "Url_anuncio"]].rename(columns={
            "FullAddress": "Endereço",
            "unit_price": "Preço (USD)",
            "unit_beds": "Quartos",
            "dist_sch": "Escola (km)",
            "dist_sup": "Supermercado (km)",
            "Url_anuncio": "Link"
        }),
        use_container_width=True,
        hide_index=True,
        column_config={"Link": st.column_config.LinkColumn()}
    )

st.caption("v16.2 PRO — 100% SEQUENCIAL • Só busca POIs APÓS df_filtrado • 5km reais • Italy-proof • 13 Nov 2025")