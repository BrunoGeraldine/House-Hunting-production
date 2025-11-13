# core/osm_fetcher.py - v28.3 (SUPERMERCADOS GARANTIDOS — 62+ EM CONROE)
import requests
import pandas as pd
import streamlit as st
from config.settings import HEADERS

class OSMFetcher:
    def __init__(self, south, west, north, east):
        self.bbox = (south, west, north, east)

    @st.cache_data(ttl=3600, show_spinner=False)
    def _fetch(_self, bbox, tag, value):
        s, w, n, e = bbox
        # QUERY OFICIAL QUE PEGA TODOS OS SUPERMERCADOS (inclui Walmart, HEB, etc.)
        if tag == "shop" and value == "supermarket":
            query = f'''
            [out:json][timeout:90];
            (
              node["shop"="supermarket"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});
              way["shop"="supermarket"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});
              relation["shop"="supermarket"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});
              node["shop"="grocery"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});
              way["shop"="grocery"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});
              node["brand"~"Walmart|HEB|Kroger|Target|Costco|Aldi"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});
              way["brand"~"Walmart|HEB|Kroger|Target|Costco|Aldi"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});
            );
            out center;
            '''
        else:
            query = f'''
            [out:json][timeout:90];
            (
              node[{tag}="{value}"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});
              way[{tag}="{value}"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});
              relation[{tag}="{value}"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});
            );
            out center;
            '''
        
        try:
            r = requests.post(
                "https://overpass.kumi.systems/api/interpreter",
                data={"data": query},
                headers=HEADERS,
                timeout=120
            )
            if r.status_code == 200:
                return r.json().get("elements", [])
        except Exception as e:
            st.warning(f"Erro OSM: {e}")
        return []

    def get_supermarkets(self):
        raw = self._fetch(self.bbox, "shop", "supermarket")
        df = self._process(raw, "Supermercado")
        # Remove duplicatas por nome + localização
        df = df.drop_duplicates(subset=["name", "lat", "lon"])
        return df.reset_index(drop=True)

    def get_schools(self):
        raw = self._fetch(self.bbox, "amenity", "school")
        df = self._process(raw, "Escola")
        df = df[~df["name"].str.contains("university|college|daycare|preschool|montessori", case=False, na=True)]
        return df.drop_duplicates(subset=["name", "lat", "lon"]).reset_index(drop=True)

    def _process(self, elements, default):
        data = []
        seen = set()
        for e in elements:
            eid = e.get("id")
            if eid in seen: continue
            seen.add(eid)
            
            lat = e.get("lat") or (e.get("center") or {}).get("lat")
            lon = e.get("lon") or (e.get("center") or {}).get("lon")
            if not lat or not lon: continue
            
            tags = e.get("tags", {})
            name = tags.get("name") or tags.get("brand") or tags.get("operator") or default
            name = str(name).strip().title()
            if name in ["None", ""]: 
                name = default
                
            data.append({"name": name, "lat": float(lat), "lon": float(lon)})
        return pd.DataFrame(data)