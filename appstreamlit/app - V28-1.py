# app.py - v28.1 (VISUAL PERFEITO + ÍCONES DIFERENTES)
import streamlit as st
from core.data_loader import load_properties
from core.osm_fetcher import OSMFetcher
from core.distance import nearest_poi
from core.map_builder import MapBuilder

st.set_page_config(layout="wide", page_title="US Rental Map v28.1", page_icon="house")
st.title("US Rental Map — Perfeito Visualmente")
st.markdown("<style>[data-testid='stApp']{background:#000;color:#FFF}</style>", unsafe_allow_html=True)

df = load_properties()
city = st.sidebar.selectbox("Cidade", sorted(df["City"].unique()))
filtered = df[df["City"] == city].copy()

beds = st.sidebar.multiselect("Quartos", sorted(filtered["unit_beds"].dropna().unique()), default=[])
price = st.sidebar.slider("Preço", int(filtered["unit_price"].min()), int(filtered["unit_price"].max()),
                          (int(filtered["unit_price"].min()), int(filtered["unit_price"].max())))

if beds:
    filtered = filtered[filtered["unit_beds"].isin(beds)]
filtered = filtered[filtered["unit_price"].between(price[0], price[1])]

st.write(f"**{len(filtered)} casas em {city}**")

center = [filtered["Lat"].mean(), filtered["Lon"].mean()]
fetcher = OSMFetcher(center[0]-0.06, center[1]-0.06, center[0]+0.06, center[1]+0.06)
supers = fetcher.get_supermarkets()
schools = fetcher.get_schools()

st.success(f"**{len(supers)} supermercados • {len(schools)} escolas K-12**")

# MAPA COM ÍCONES CORRETOS
builder = MapBuilder(center)
builder.add_supermarkets(supers)
builder.add_schools(schools)

for _, row in filtered.iterrows():
    ns = nearest_poi(supers, row["Lat"], row["Lon"], "supermercado")
    nsc = nearest_poi(schools, row["Lat"], row["Lon"], "escola")
    builder.add_home(row, ns, nsc)

builder.render()
st.caption("v28.1 • 12 Nov 2025")