# House Hunting - Real Estate Visualization Pipeline

Complete system for capturing, transforming and interactively visualizing real estate data from the Houston region. The pipeline processes raw data, transforms it into clean format and presents it on an interactive map with multiple features.

## 📋 Project Architecture

```
House-Hunting-production/
├── dataset/
│   ├── bronze/               # Processed data (cleaned)
│   │   └── Houston_bronze.csv
│   └── raw/                  # Raw data (raw)
├── appstreamlit/
│   └── app.py               # Main application (Streamlit)
├── scrapyfly_zillow_all.py  # Extraction script
├── 3_ciclo_scrapyfly_zillow_all.py
└── README.md
```

## 🔄 Data Flow

```
Zillow API (via ScrapFly)
        ↓
scrapyfly_zillow_all.py (Extract)
        ↓
dataset/raw/*.csv
        ↓
raw-to-bronze.py (Transform)
        ↓
dataset/bronze/Houston_bronze.csv
        ↓
app.py (Streamlit Visualization)
        ↓
Interactive Map + Filters
```

## 1️⃣ Data Extraction (Extract)

### `scrapyfly_zillow_all.py`
Main script that captures real estate data from Zillow through the ScrapFly API.

**Features:**
- Capture real estate listings with advanced filters
- Support for multiple cities
- Filters by:
  - Maximum price
  - Minimum number of bedrooms
  - Minimum number of bathrooms (supports decimals: 1.5, 2.5, etc)
  - Number of pages to search

**Output:**
- CSV files in `dataset/raw/`
- Structure contains: price, address, coordinates, ad URL, etc.

### `3_ciclo_scrapyfly_zillow_all.py`
Simplified version with pre-configured parameters for quick execution:
```python
city = "The Woodlands,TX"
price_input = 3000
beds_input = 2
baths_input = 1.5
pag_input = 10
```

## 2️⃣ Data Transformation (Transform)

### `raw-to-bronze.py`
Cleaning and standardization script that processes raw data.

**Operations Performed:**
1. **Merge**: Combines multiple CSV files from `raw/`
2. **Cleaning**: Removes duplicates and null values
3. **Standardization**: Normalizes addresses and data formats
4. **Expansion**: Breaks down nested data (units, coordinates)
5. **Derivation**: Creates new useful columns
6. **Traceability**: Maintains `source_file` column for data origin

**Output:**
- `dataset/bronze/Houston_bronze.csv` (processed data)

## 3️⃣ Interactive Visualization (Visualization)

### `appstreamlit/app.py`
Interactive web application built with **Streamlit** and **Folium** that provides a dynamic real estate map.

## 🗺️ How the Main Code Works

### Initialization
```python
st.set_page_config(layout="wide", page_title="Mapa Interativo de Imóveis...")
```
- Configures layout in "wide" mode for better space utilization
- Sets dark theme via custom CSS

### Data Loading
```python
@st.cache_data
def load_data(csv_file):
    df = pd.read_csv(csv_file)
    df = df.dropna(subset=['Lat', 'Lon', 'unit_price'])
    df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce')
    return df
```
- Reads `Houston_bronze.csv` from `dataset/bronze/` directory
- Removes records without geographic coordinates
- Converts prices to numeric format
- `@st.cache_data` optimizes loading performance

### Sidebar Filters
```python
# Filter 1: Price Range (slider)
unit_price_range = st.sidebar.slider("Faixa de preço", min_unit_price, max_unit_price, ...)

# Filter 2: Number of Bedrooms (multi-select)
beds_quantity = st.sidebar.multiselect("Quantidade de quartos", ...)
```
- **Price Range**: Interactive slider shows min/max of data
- **Bedrooms**: Multi-select allows choosing one or several quantities
- Filters are applied in real-time: `filtered_df = df[conditions]`

### Distance Calculation

#### Haversine (actual distance between points)
```python
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c
```
- Calculates precise geodesic distance between two points on Earth
- Used to find nearest points of interest
- Result in kilometers

### Pre-configured Points of Interest

**Supermarkets** (hardcoded data):
```python
supermarkets = pd.DataFrame([
    {"name": "Walmart", "lat": 29.922501..., "lon": -95.413658...},
    {"name": "Target", "lat": 30.170268..., "lon": -95.452721...},
    {"name": "Costco", "lat": 29.955045..., "lon": -95.547673...},
    {"name": "H-E-B", "lat": 29.995824..., "lon": -95.576231...},
    ...
])
```

**Parks** (hardcoded data):
```python
parks = pd.DataFrame([
    {"name": "Memorial Park", "lat": 29.764777, "lon": -95.441254},
    {"name": "Buffalo Bayou Park", "lat": 29.762115, "lon": -95.383207},
    ...
])
```

### Map Rendering

**Initialization**:
```python
map_center = [filtered_df['Lat'].mean(), filtered_df['Lon'].mean()]
m = folium.Map(location=map_center, zoom_start=11)
```
- Center automatically based on mean coordinates of filtered properties
- Default zoom level at 11 (neighborhoods)

**Supermarket Markers**:
```python
folium.Marker(
    location=[s["lat"], s["lon"]],
    popup=f'<b>{s["name"]}</b>',
    icon=folium.Icon(color='blue', icon='shopping-cart', prefix='fa')
).add_to(m)
```
- Blue icon with shopping cart symbol
- PopUp on click shows establishment name

**Park Markers**:
```python
folium.Marker(
    location=[p["lat"], p["lon"]],
    popup=f'<b>{p["name"]}</b>',
    icon=folium.Icon(color='yellow', icon='park-cart', prefix='fa')
).add_to(m)
```
- Yellow icon for easy identification

**Property Markers**:
```python
for _, row in filtered_df.iterrows():
    lat = row.get('Lat')
    lon = row.get('Lon')
    
    # Finds nearest supermarket
    nearest_super = supermarkets.loc[supermarkets['distance_km'].idxmin()]
    
    # Finds nearest park
    nearest_park = parks.loc[parks['distance_km'].idxmin()]
```
- Iterates through each filtered property
- Calculates distance to ALL supermarkets
- Identifies closest using `idxmin()`
- Repeats process for parks

### Interactive Property PopUp

Each property displays a rich HTML popup with:
1. **Basic Information**:
   - Price (💰)
   - Number of bedrooms (🛏)
   - Full address (📍)

2. **Clickable Buttons**:

   - **🔗 Zillow**: Direct link to the listing
     ```python
     zillow_url = row.get('Url_anuncio', '#')
     ```

   - **📌 Google Maps**: Opens location on map
     ```python
     google_maps_url = f"https://www.google.com/maps?q={lat},{lon}"
     ```

   - **🚗 Route to Supermarket**: Directions to nearest supermarket
     ```python
     directions_super_url = f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={nearest_super['lat']},{nearest_super['lon']}&travelmode=driving"
     ```
     - Mode: Driving
     - Distance displayed in km (ex: "🚗 Route to Walmart (2.3 km)")

   - **🚶 Path to Park**: Directions to nearest park
     ```python
     directions_park_url = f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={nearest_park['lat']},{nearest_park['lon']}&travelmode=walking"
     ```
     - Mode: Walking
     - Distance displayed in km

### Button Styling

Each button has custom CSS:
```python
popup_html = f"""
    <a href="{zillow_url}" target="_blank" style="
        display:inline-block; 
        background-color:#006AFF;  <!-- Blue -->
        color:white; 
        padding:6px 12px; 
        border-radius:6px;
        text-decoration:none; 
        font-weight:bold; 
        margin:4px;
    ">🔗 Zillow</a>
"""
```
- Colors differentiated by functionality
- Padding and border-radius for better UX
- `target="_blank"` opens in new tab

### Button Colors

| Button | Color | Code |
|--------|-------|------|
| Zillow | Blue | #006AFF |
| Google Maps | Green | #34A853 |
| Supermarket | Orange | #FF9800 |
| Park | Light Green | #4CAF50 |

### Final Rendering

```python
st_folium(m, width=1000, height=600)
```
- Integrates Folium map into Streamlit
- Dimensions: 1000px wide × 600px high
- Fully interactive: zoom, pan, click on markers

## 🚀 How to Use

### Install Dependencies
```bash
pip install streamlit folium streamlit-folium pandas
```

### Run the Application
```bash
streamlit run appstreamlit/app.py
```

### Complete Workflow
1. **Capture data**:
   ```bash
   python scrapyfly_zillow_all.py
   ```

2. **Process data**:
   ```bash
   python dataset/raw-to-bronze.py
   ```

3. **Visualize**:
   ```bash
   streamlit run appstreamlit/app.py
   ```
   - The application will open at `http://localhost:8501`

## ⚙️ Technical Resources

| Component | Technology | Function |
|-----------|-----------|----------|
| Backend | Python 3.8+ | Processing |
| Web Framework | Streamlit | Interactive interface |
| Maps | Folium | Geographic visualization |
| Data | Pandas | DataFrame manipulation |
| Scraping | ScrapFly API | Zillow data collection |
| Math | Math | Distance calculation |

## 📊 Data Structure (CSV)

Expected columns in `Houston_bronze.csv`:
```
Lat              → Latitude (float)
Lon              → Longitude (float)
unit_price       → Property price (float)
unit_beds        → Number of bedrooms (int)
FullAddress      → Full address (string)
Url_anuncio      → Zillow ad URL (string)
source_file      → Data origin file (string)
```

## 💡 Main Features

✅ **Interactive Map**: Zoom, pan and click on markers
✅ **Real-time Filters**: Price and number of bedrooms
✅ **Proximity Intelligence**: Automatically locates nearby points of interest
✅ **Contextual Links**: Zillow, Google Maps and routes with different modes
✅ **Dark Theme**: Easy-to-view dark interface
✅ **Responsive**: Layout adaptable to different screen sizes
✅ **Data Cache**: Optimizes loading performance

## 🔒 Important Notes

- The capture script uses rate limiting via ScrapFly to avoid blocking
- Data is saved incrementally to prevent loss on interruptions
- The bronze CSV must contain valid coordinates (Lat, Lon) to work
- Points of interest (supermarkets and parks) are pre-configured
- The calculated distance is geodesic (actual distance on Earth, not Euclidean)