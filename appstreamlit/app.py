###### INTERACTIVE MAP WITH CLICKABLE LINKS TO PROPERTY LISTINGS ######

# app.py - Real Estate Interactive Map Visualization
import math
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

#st.title("Interactive Real Estate Map in Houston (Clickable)")

# ------------------------------
# Initial Streamlit Configuration
# ------------------------------
st.set_page_config(
    layout="wide",  # Set layout to "wide"
    initial_sidebar_state="auto",
    page_title="Interactive Real Estate Map in Houston Region (Clickable)",
    page_icon="📈"
)

# Set dark theme explicitly (optional, can also be configured in config.toml)
st.markdown(
    """
    <style>
    /* Force dark theme */
    [data-testid="stApp"] {
        background-color: #1E1E1E;  /* Dark background color */
        color: #FFFFFF;  /* White text */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Function to calculate distance between 2 coordinates
def calc_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)


# -------------------------------
# Load CSV Data
@st.cache_data
def load_data(csv_file):
    df = pd.read_csv(csv_file)
    df = df.dropna(subset=['Lat', 'Lon', 'unit_price'])
    df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce')
    return df



#df = load_data("https://brunojornadadedados.s3.us-east-1.amazonaws.com/api-realtor_city/redfin_solding_all.csv")
df = load_data("../dataset/bronze/Houston_bronze.csv")


# -------------------------------
# Sidebar filtros
st.sidebar.header("Filtros")
min_unit_price = int(df['unit_price'].min())
max_unit_price = int(df['unit_price'].max())
unit_price_range = st.sidebar.slider("Faixa de preço", min_unit_price, max_unit_price, (min_unit_price, max_unit_price))

filtered_df = df[(df['unit_price'] >= unit_price_range[0]) & (df['unit_price'] <= unit_price_range[1])]

beds_quantity = st.sidebar.multiselect("Quantidade de quartos", options=sorted(df['unit_beds'].dropna().unique()), default=sorted(df['unit_beds'].dropna().unique()))
if beds_quantity:
    filtered_df = filtered_df[filtered_df['unit_beds'].isin(beds_quantity)]

st.write(f"Imóveis encontrados: {len(filtered_df)}")

# -------------------------------
# Criar mapa centralizado
map_center = [filtered_df['Lat'].mean(), filtered_df['Lon'].mean()]
m = folium.Map(location=map_center, zoom_start=11)

# -------------------------------
# Supermercados
supermarkets = pd.DataFrame([
    {"name": "Walmart", "lat": 29.922501830798883, "lon": -95.41365858731908}, 
    {"name": "Walmart", "lat": 30.077729944405423, "lon": -95.38729244393436}, 
    {"name": "Walmart", "lat": 30.069205213415394, "lon": -95.41074417927655}, 
    {"name": "Walmart", "lat": 30.003462974400296, "lon": -95.47321130269982}, 
    {"name": "Walmart", "lat": 30.210006622053395, "lon": -95.45890834239746}, 

    {"name": "Target", "lat": 30.17026853288784, "lon": -95.45272148246633},
    {"name": "Target", "lat": 30.08786626858349, "lon": -95.52081306108647},
    {"name": "Target", "lat": 30.05415756331383, "lon": -95.43451647239814},
    {"name": "Target", "lat": 29.975284709213717, "lon": -95.51227584550033},

    {"name": "Costco", "lat": 29.955045320146994, "lon": -95.54767363049966},


    {"name": "Sam's Club", "lat": 29.964046078227206, "lon": -95.54681355662805},

    {"name": "H-E-B", "lat": 29.995824969642012, "lon": -95.5762311946599},
    {"name": "H-E-B", "lat": 30.1637968136592, "lon": -95.46680211965837},
    {"name": "H-E-B", "lat": 30.182468423589118, "lon": -95.53341958785808},
    {"name": "H-E-B", "lat": 30.149413446242157, "lon": -95.54058205634084},
    {"name": "H-E-B", "lat": 30.128846499514538, "lon": -95.44514248266452},
    {"name": "H-E-B", "lat": 30.229070212533912, "lon": -95.49168495616046},
    {"name": "H-E-B", "lat": 30.224958987972332, "lon": -95.56002935889994},
    {"name": "H-E-B", "lat": 30.055502165530353, "lon": -95.55570375979246},
    {"name": "H-E-B", "lat": 30.027998241730693, "lon": -95.48515800280508},
    {"name": "H-E-B", "lat": 30.10858425535382, "lon": -95.33893543044405},
    {"name": "H-E-B", "lat": 30.073335948900567, "lon": -95.39858842016348},
    {"name": "H-E-B", "lat": 30.206754173199442, "lon": -95.41995005622451},

])

# -------------------------------
# Parques
parks = pd.DataFrame([
    {"name": "Memorial Park", "lat": 29.764777, "lon": -95.441254},
    {"name": "Buffalo Bayou Park", "lat": 29.762115, "lon": -95.383207},
    {"name": "Hermann Park", "lat": 29.721736, "lon": -95.389328},
    {"name": "The Woodlands Park", "lat": 30.162962, "lon": -95.469383},
    {"name": "Pundt Park", "lat": 30.058789, "lon": -95.375004},
    {"name": "Champions Golf Club", "lat": 29.98422815376261, "lon": -95.52355299583914},
    {"name": "Champion Forest Park", "lat": 29.992463765268795, "lon": -95.54466320432775},
])


# -------------------------------
# Função para calcular distância em km (Haversine)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # raio da Terra em km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


for _, s in supermarkets.iterrows():
    folium.Marker(
        location=[s["lat"], s["lon"]],
        popup=f'<b>{s["name"]}</b>',
        icon=folium.Icon(color='blue', icon='shopping-cart', prefix='fa')
    ).add_to(m)

for _, s in parks.iterrows():
    folium.Marker(
        location=[s["lat"], s["lon"]],
        popup=f'<b>{s["name"]}</b>',
        icon=folium.Icon(color='yellow', icon='park-cart', prefix='fa')
    ).add_to(m)


# -------------------------------
# Adicionar imóveis com popups ricos
for _, row in filtered_df.iterrows():
    lat = row.get('Lat')
    lon = row.get('Lon')

    if pd.isna(lat) or pd.isna(lon):
        continue

    # Supermercado mais próximo
    supermarkets['distance_km'] = supermarkets.apply(lambda s: haversine(lat, lon, s['lat'], s['lon']), axis=1)
    nearest_super = supermarkets.loc[supermarkets['distance_km'].idxmin()]

    # Parque mais próximo
    parks['distance_km'] = parks.apply(lambda p: haversine(lat, lon, p['lat'], p['lon']), axis=1)
    nearest_park = parks.loc[parks['distance_km'].idxmin()]

    # URLs
    zillow_url = row.get('Url_anuncio', '#')
    google_maps_url = f"https://www.google.com/maps?q={lat},{lon}"
    street_view_url = f"https://www.google.com/maps?q=&layer=c&cbll={lat},{lon}"
    directions_super_url = f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={nearest_super['lat']},{nearest_super['lon']}&travelmode=driving"
    directions_park_url = f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={nearest_park['lat']},{nearest_park['lon']}&travelmode=walking"

    # HTML do popup
    popup_html = f"""
        <div style="font-size:14px; text-align:center;">
            <b>💰 Preço:</b> ${row.get('unit_price', '')}<br>
            <b>🛏 Quartos:</b> {row.get('unit_beds', '')}<br>
            <b>📍 Endereço:</b> {row.get('FullAddress', '')}<br><br>

            <a href="{zillow_url}" target="_blank" style="
                display:inline-block; background-color:#006AFF;
                color:white; padding:6px 12px; border-radius:6px;
                text-decoration:none; font-weight:bold; margin:4px;
            ">🔗 Zillow</a>

            <a href="{google_maps_url}" target="_blank" style="
                display:inline-block; background-color:#34A853;
                color:white; padding:6px 12px; border-radius:6px;
                text-decoration:none; font-weight:bold; margin:4px;
            ">📌 Google Maps</a>

           
            <a href="{directions_super_url}" target="_blank" style="
                display:inline-block; background-color:#FF9800;
                color:white; padding:6px 12px; border-radius:6px;
                text-decoration:none; font-weight:bold; margin:4px;
            ">🚗 Rota até {nearest_super['name']} ({nearest_super['distance_km']:.1f} km)</a>

            <a href="{directions_park_url}" target="_blank" style="
                display:inline-block; background-color:#4CAF50;
                color:white; padding:6px 12px; border-radius:6px;
                text-decoration:none; font-weight:bold; margin:4px;
            ">🚶 Caminho até {nearest_park['name']} ({nearest_park['distance_km']:.1f} km)</a>
        </div>
    """

    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_html, max_width=340),
        icon=folium.Icon(color='red', icon='home')
    ).add_to(m)

# -------------------------------
# Mostrar mapa no Streamlit
st_folium(m, width=1000, height=600)
