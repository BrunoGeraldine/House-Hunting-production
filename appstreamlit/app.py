# app.py - US Rental Map PRO v28.3 (MODULAR + ESTÁVEL)
import math
import folium
import requests
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from core.map_builder import MapBuilder

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

# === 2. FILTROS NO SIDEBAR ===
st.sidebar.header("Filtros de Localização")

available_states = sorted(df_original["State"].unique())
if "state" not in st.session_state:
    st.session_state.state = available_states[0] if available_states else "TX"

st.session_state.state = st.sidebar.selectbox(
    "Estado",
    options=available_states,
    index=available_states.index(st.session_state.state) if st.session_state.state in available_states else 0,
    key="state_selectbox"
)

cities_in_state = sorted(df_original[df_original["State"] == st.session_state.state]["City"].str.title().unique())
if "city" not in st.session_state:
    st.session_state.city = ""

st.session_state.city = st.sidebar.selectbox(
    "Cidade",
    options=[""] + cities_in_state,
    index=0 if st.session_state.city == "" else (cities_in_state.index(st.session_state.city) + 1 if st.session_state.city in cities_in_state else 0),
    key="city_selectbox"
)

beds_options = sorted(df_original["unit_beds"].dropna().unique())
beds_sel = st.sidebar.multiselect("Quartos", beds_options, default=beds_options[:2])

price_min = int(df_original["unit_price"].min())
price_max = int(df_original["unit_price"].max())
price_range = st.sidebar.slider("Preço (USD)", price_min, price_max, (price_min, price_max + 1000))

# === 4. APLICA FILTROS ===
df_filtrado = df_original[
    (df_original["State"] == st.session_state.state) &
    (df_original["City"].str.title() == st.session_state.city.title() if st.session_state.city else True) &
    (df_original["unit_beds"].isin(beds_sel)) &
    (df_original["unit_price"].between(price_range[0], price_range[1]))
].copy()

if not df_filtrado.empty:
    df_filtrado = df_filtrado.sort_values("unit_price").head(50).reset_index(drop=True)
    center = [df_filtrado["Lat"].mean(), df_filtrado["Lon"].mean()]
else:
    st.warning("Nenhum imóvel encontrado.")
    center = [30.2672, -95.6000]
    df_filtrado = pd.DataFrame()

st.write(f"**{len(df_filtrado)} imóveis encontrados**")

# === 5. BUSCA POIs (ROBUSTA) ===
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

@st.cache_data(ttl=7200)
def get_pois_around_houses(_hash, lat_list, lon_list):
    if not lat_list: return [], []
    points = ",".join([f"{la},{lo}" for la, lo in zip(lat_list, lon_list)])
    query = f'''
    [out:json][timeout:60];
    (
      nwr["shop"~"supermarket|grocery"]["name"](around:5000,{points});
      nwr["brand"~"Walmart|Best Buy|Savers|HEB|Kroger|Target|Costco|Aldi",i](around:5000,{points});
      nwr["amenity"="school"](around:5000,{points});
    );
    out center;
    '''
    servers = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter"
    ]
    for server in servers:
        try:
            r = requests.post(server, data={"data": query}, timeout=60)
            if r.status_code == 200:
                supers, schools = [], []
                for e in r.json().get("elements", []):
                    lat = e.get("lat") or e.get("center", {}).get("lat")
                    lon = e.get("lon") or e.get("center", {}).get("lon")
                    if not lat or not lon: continue
                    name = (e["tags"].get("name") or e["tags"].get("brand") or "Local").title()
                    if e["tags"].get("shop") or "brand" in e["tags"]:
                        supers.append([float(lat), float(lon), name])
                    elif e["tags"].get("amenity") == "school":
                        if not any(x in name.lower() for x in ["university", "college", "daycare", "preschool"]):
                            schools.append([float(lat), float(lon), name])
                return supers, schools
        except:
            continue
    return [], []

with st.spinner("Buscando POIs..."):
    hash_key = f"{st.session_state.state}_{st.session_state.city}_{len(df_filtrado)}"
    supers, schools = get_pois_around_houses(hash_key, df_filtrado["Lat"].tolist(), df_filtrado["Lon"].tolist())

# === CONVERTE PARA DATAFRAMES ===
supermarkets_df = pd.DataFrame(supers, columns=["lat", "lon", "name"]) if supers else pd.DataFrame(columns=["lat", "lon", "name"])
schools_df = pd.DataFrame(schools, columns=["lat", "lon", "name"]) if schools else pd.DataFrame(columns=["lat", "lon", "name"])

# === 6. CONSTRÓI O MAPA MODULAR ===
map_builder = MapBuilder(center=center)
map_builder.add_supermarkets(supermarkets_df)
map_builder.add_schools(schools_df)

for _, row in df_filtrado.iterrows():
    # Supermercado mais próximo
    if not supermarkets_df.empty:
        dists = supermarkets_df.apply(lambda r: haversine(row["Lat"], row["Lon"], r["lat"], r["lon"]), axis=1)
        idx = dists.idxmin()
        ns = supermarkets_df.loc[idx].to_dict()
        ns["dist"] = dists[idx]
    else:
        ns = {"lat": 0, "lon": 0, "name": "N/A", "dist": 99}

    # Escola mais próxima
    if not schools_df.empty:
        dists = schools_df.apply(lambda r: haversine(row["Lat"], row["Lon"], r["lat"], r["lon"]), axis=1)
        idx = dists.idxmin()
        nsc = schools_df.loc[idx].to_dict()
        nsc["dist"] = dists[idx]
    else:
        nsc = {"lat": 0, "lon": 0, "name": "N/A", "dist": 99}

    map_builder.add_home(row, ns, nsc)

# === 7. EXIBE O MAPA ===
st_folium(map_builder.get_map(), width=1200, height=550, key="rental_map")

## === 8. TABELA ===
#if not df_filtrado.empty:
#    tabela = df_filtrado.copy()
#    tabela["dist_sup"] = tabela.apply(lambda r: min([haversine(r["Lat"], r["Lon"], s[0], s[1]) for s in supers], default=99), axis=1)
#    tabela["dist_sch"] = tabela.apply(lambda r: min([haversine(r["Lat"], r["Lon"], s[0], s[1]) for s in schools], default=99), axis=1)
#    tabela = tabela.sort_values(by=["unit_price", "dist_sch", "dist_sup"])
#    st.subheader("Ranking Final")
#    st.dataframe(
#        tabela[["FullAddress", "unit_price", "unit_beds", "dist_sch", "dist_sup", "Url_anuncio"]].rename(columns={
#            "FullAddress": "Endereço", "unit_price": "Preço", "unit_beds": "Quartos",
#            "dist_sch": "Escola (km)", "dist_sup": "Supermercado (km)", "Url_anuncio": "Link"
#        }),
#        use_container_width=True, hide_index=True,
#        column_config={"Link": st.column_config.LinkColumn()}
#    )

# === 8. TABELA FINAL COM NOME DOS POIs ===
if not df_filtrado.empty:
    tabela = df_filtrado.copy()

    # Calcula distância e nome do supermercado mais próximo
    def get_closest_sup(row):
        if supermarkets_df.empty:
            return "N/A", 99
        dists = supermarkets_df.apply(
            lambda r: haversine(row["Lat"], row["Lon"], r["lat"], r["lon"]), axis=1
        )
        idx = dists.idxmin()
        return supermarkets_df.loc[idx, "name"], dists[idx]

    # Calcula distância e nome da escola mais próxima
    def get_closest_sch(row):
        if schools_df.empty:
            return "N/A", 99
        dists = schools_df.apply(
            lambda r: haversine(row["Lat"], row["Lon"], r["lat"], r["lon"]), axis=1
        )
        idx = dists.idxmin()
        return schools_df.loc[idx, "name"], dists[idx]

    # Aplica funções
    tabela[["sup_name", "dist_sup"]] = tabela.apply(
        lambda row: pd.Series(get_closest_sup(row)), axis=1
    )
    tabela[["sch_name", "dist_sch"]] = tabela.apply(
        lambda row: pd.Series(get_closest_sch(row)), axis=1
    )

    # Ordena por preço + proximidade
    tabela = tabela.sort_values(by=["unit_price", "dist_sch", "dist_sup"])

    # Exibe tabela
    st.subheader("Ranking Final: Preço + Proximidade")
    st.dataframe(
        tabela[[
            "FullAddress", "unit_price", "unit_beds",
            "sch_name", "dist_sch",
            "sup_name", "dist_sup",
            "Url_anuncio"
        ]].rename(columns={
            "FullAddress": "Endereço",
            "unit_price": "Preço (USD)",
            "unit_beds": "Quartos",
            "sch_name": "Escola mais próxima",
            "dist_sch": "Dist. Escola (km)",
            "sup_name": "Supermercado mais próximo",
            "dist_sup": "Dist. Supermercado (km)",
            "Url_anuncio": "Link"
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Link": st.column_config.LinkColumn(),
            "Preço (USD)": st.column_config.NumberColumn(
                format="%,.0f",
                prefix="$"
            ),
            "Dist. Escola (km)": st.column_config.NumberColumn(
                format="%.1f",
                suffix=" km"
            ),
            "Dist. Supermercado (km)": st.column_config.NumberColumn(
                format="%.1f",
                suffix=" km"
            ),
        }
        #column_config={
        #    "Link": st.column_config.LinkColumn(),
        #    "Preço (USD)": st.column_config.NumberColumn(format="$%,.2f"),
        #    "Dist. Escola (km)": st.column_config.NumberColumn(format="%.1f km"),
        #    "Dist. Supermercado (km)": st.column_config.NumberColumn(format="%.1f km"),
        #}
    )#
else:
    st.info("Nenhum imóvel encontrado com os filtros aplicados.")

st.caption("vfuncional PRO — Modular • Estável • Italy-proof • 13 Nov 2025")