import math
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    a = math.sin(math.radians(lat2 - lat1) / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2 - lon1) / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def nearest_poi(df, lat, lon, name):
    if df.empty:
        return {"name": f"Sem {name}", "lat": lat, "lon": lon, "dist": 0}
    row = min(df.iterrows(), key=lambda x: haversine(lat, lon, x[1]["lat"], x[1]["lon"]))[1]
    return {"name": row["name"], "lat": row["lat"], "lon": row["lon"], "dist": haversine(lat, lon, row["lat"], row["lon"])}