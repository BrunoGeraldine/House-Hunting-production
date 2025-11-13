import pandas as pd
import streamlit as st
from config.settings import CSV_PATH

@st.cache_data(ttl=86400)
def load_properties():
    df = pd.read_csv(CSV_PATH)
    df = df.dropna(subset=["Lat", "Lon", "unit_price", "City"])
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    return df.dropna(subset=["unit_price"])