# core/map_builder.py - v28.1 (ÍCONES CORRETOS + VISUAL PERFEITO)
import folium
import streamlit as st
from streamlit_folium import st_folium

class MapBuilder:
    def __init__(self, center):
        self.map = folium.Map(
            location=center,
            zoom_start=12,
            tiles="CartoDB positron"
        )

    def add_supermarkets(self, df):
        for _, r in df.iterrows():
            folium.Marker(
                location=[r["lat"], r["lon"]],
                popup=f"<b style='color:#1E90FF'>Supermercado: {r['name']}</b>",
                icon=folium.Icon(color="blue", icon="shopping-cart", prefix="fa"),
                tooltip=r["name"]
            ).add_to(self.map)

    def add_schools(self, df):
        for _, r in df.iterrows():
            folium.Marker(
                location=[r["lat"], r["lon"]],
                popup=f"<b style='color:#FF9800'>Escola: {r['name']}</b>",
                icon=folium.Icon(color="orange", icon="graduation-cap", prefix="fa"),
                tooltip=r["name"]
            ).add_to(self.map)

    def add_home(self, row, ns, nsc):
        popup = f"""
        <div style="width:360px;font-family:Arial;background:#111;color:white;padding:12px;border-radius:12px">
            <b style="font-size:19px;color:#FF5252">${row['unit_price']:,.0f}</b> • {row['unit_beds']} quartos<br>
            <b style="color:#FFF">{row.get('FullAddress', 'Endereço não informado')}</b><br><br>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
                <a href="{row.get('Url_anuncio','#')}" target="_blank" 
                   style="background:#006AFF;color:white;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:bold">
                   Zillow
                </a>
                <a href="https://www.google.com/maps?q={row['Lat']},{row['Lon']}" target="_blank"
                   style="background:#34A853;color:white;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:bold">
                   Maps
                </a>
            </div>
            <br>
            <a href="https://www.google.com/maps/dir/?api=1&origin={row['Lat']},{row['Lon']}&destination={ns['lat']},{ns['lon']}&travelmode=driving" 
               target="_blank" style="display:block;background:#FF9800;color:white;padding:10px;border-radius:8px;text-decoration:none;margin:8px 0">
               Dirigir até {ns['name'][:28]} ({ns['dist']:.1f}km)
            </a>
            <a href="https://www.google.com/maps/dir/?api=1&origin={row['Lat']},{row['Lon']}&destination={nsc['lat']},{nsc['lon']}&travelmode=walking" 
               target="_blank" style="display:block;background:#9C27B0;color:white;padding:10px;border-radius:8px;text-decoration:none">
               Caminhar até {nsc['name'][:28]} ({nsc['dist']:.1f}km)
            </a>
        </div>
        """
        folium.Marker(
            location=[row["Lat"], row["Lon"]],
            popup=folium.Popup(popup, max_width=400),
            icon=folium.Icon(color="red", icon="home", prefix="fa"),
            tooltip=f"${row['unit_price']:,.0f} • {row['unit_beds']} quartos"
        ).add_to(self.map)

    def render(self):
        return st_folium(self.map, width=1200, height=550, returned_objects=[])