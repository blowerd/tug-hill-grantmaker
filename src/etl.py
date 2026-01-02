import requests
import json
import pandas as pd
import sqlite3
import uuid
import random
import os
from pathlib import Path
from database import get_connection, reset_db

# --- DYNAMIC PATH CONFIGURATION ---
# Get the directory where THIS script (etl.py) is located
# (e.g., /Users/you/project/src)
SCRIPT_DIR = Path(__file__).resolve().parent

# Go up one level to find the Project Root
# (e.g., /Users/you/project)
PROJECT_ROOT = SCRIPT_DIR.parent

# Now define the path relative to the root
SVI_CSV_PATH = PROJECT_ROOT / "data" / "svi_interactive_map.csv"

# --- REST OF CONFIG ---
COUNTIES = ["045", "049", "089"]
STATE = "36"
TIGER_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/8/query"
ACS_URL = "https://api.census.gov/data/2023/acs/acs5/profile"

def fetch_regional_tracts():
    print(f"🌍 Fetching Geography for counties: {COUNTIES}...")
    # SQL-like IN clause for the API
    county_list = ",".join([f"'{c}'" for c in COUNTIES])
    params = {
        "where": f"STATE='{STATE}' AND COUNTY IN ({county_list})",
        "outFields": "GEOID,NAME",
        "f": "geojson"
    }
    
    try:
        resp = requests.get(TIGER_URL, params=params, timeout=30)
        data = resp.json()
        features = []
        for f in data.get('features', []):
            props = f.get('properties', {})
            geoid = props.get('GEOID')
            # Strict Tract Check (11 digits)
            if geoid and len(geoid) == 11:
                features.append({
                    'geoid': geoid,
                    'name': props.get('NAME'),
                    'geometry': json.dumps(f.get('geometry'))
                })
        print(f"✅ Loaded {len(features)} tracts.")
        return features
    except Exception as e:
        print(f"❌ Geo Error: {e}")
        return []

def fetch_acs_demographics():
    print("📊 Fetching Demographics (Race, Age, Ins, Broadband)...")
    # Vars: Total, Under18, Senior, White, Black, Hisp, Uninsured, Broadband
    vars = "DP05_0001E,DP05_0019E,DP05_0024E,DP05_0037E,DP05_0038E,DP05_0071E,DP03_0099PE,DP02_0153PE"
    params = {"get": vars, "for": "tract:*", "in": f"state:{STATE}"}
    
    try:
        resp = requests.get(ACS_URL, params=params, timeout=30)
        rows = resp.json()
        data = {}
        for r in rows[1:]:
            geoid = r[-3] + r[-2] + r[-1]
            if r[-2] not in COUNTIES: continue 
            
            total = int(r[0]) if r[0] else 0
            if total == 0: continue

            def pct(n): return round((int(n or 0)/total)*100, 1)
            
            data[geoid] = {
                "total_pop": total,
                "pct_under_18": pct(r[1]),
                "pct_senior": pct(r[2]),
                "pct_white": pct(r[3]),
                "pct_black": pct(r[4]),
                "pct_hispanic": pct(r[5]),
                "pct_uninsured": float(r[6]) if r[6] else 0.0,
                "pct_broadband": float(r[7]) if r[7] else 0.0
            }
        return data
    except Exception as e:
        print(f"❌ ACS Error: {e}")
        return {}

def load_svi_data():
    print(f"📈 Loading SVI from {SVI_CSV_PATH}...")
    try:
        # 1. Load CSV (Ensure FIPS is string to keep leading zeros)
        df = pd.read_csv(SVI_CSV_PATH, dtype=str)
        
        # 2. Normalize Columns (Handle variations in column names)
        # We need a 'FIPS' column and an 'RPL_THEMES' (Overall SVI) column
        cols = [c.upper() for c in df.columns]
        
        # Find FIPS column
        fips_col = next((c for c in df.columns if c.upper() in ['FIPS', 'GEOID', 'STCOFIPS']), None)
        # Find SVI column (RPL_THEMES is standard, but check for 'SVI', 'OVERALL')
        svi_col = next((c for c in df.columns if c.upper() in ['RPL_THEMES', 'SVI', 'RPL_THEMES_OVERALL']), None)

        if not fips_col or not svi_col:
            print("⚠️ Could not identify FIPS or SVI columns. Checking names...")
            print(f"Columns found: {df.columns.tolist()}")
            return {}

        # 3. Create Mapping
        svi_map = {}
        for _, row in df.iterrows():
            fips = str(row[fips_col])
            try:
                val = float(row[svi_col])
                # Filter out -999 (CDC missing data code)
                if val >= 0 and val <= 1:
                    svi_map[fips] = val
            except:
                continue
                
        print(f"✅ Mapped SVI for {len(svi_map)} tracts.")
        return svi_map

    except Exception as e:
        print(f"⚠️ SVI CSV Load Error: {e}")
        return {}

def run_etl():
    reset_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Gather Data
    tracts = fetch_regional_tracts()
    demos = fetch_acs_demographics()
    svi_map = load_svi_data()
    
    print("💾 Saving to Database...")
    for t in tracts:
        tid = t['geoid']
        
        # A. SVI Logic: Use Real CSV, or default to 0.5 (Average)
        svi = svi_map.get(tid, 0.5)
        
        # B. Demo Logic: Use Real ACS, or empty dict
        d = demos.get(tid, {})
        
        # C. Insert Tract
        cursor.execute(
            "INSERT INTO raw_tracts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (tid, f"Tract {t['name']}", t['geometry'], svi, 
             0.0, 0.0, 0.0, json.dumps(d))
        )
        
        # D. Asset Simulation (For "Hub vs Desert" Logic)
        # Since we lack real asset data for 3 counties, we simulate based on SVI
        # High SVI = High chance of Desert (0 assets)
        # Low SVI = High chance of Hub (3+ assets)
        weights = [svi*5, (1-svi)*5]
        num_assets = random.choices([0, 3], weights=weights, k=1)[0]
        
        assets_types = ['School', 'Library', 'Clinic', 'Community Center']
        for _ in range(num_assets):
            cursor.execute("INSERT INTO raw_assets VALUES (?, ?, ?)",
                           (str(uuid.uuid4()), tid, random.choice(assets_types)))

    conn.commit()
    count = cursor.execute("SELECT count(*) FROM raw_tracts").fetchone()[0]
    conn.close()
    print(f"🚀 ETL Complete: Database populated with {count} tracts.")

if __name__ == "__main__":
    run_etl()