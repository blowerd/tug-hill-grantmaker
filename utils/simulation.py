import pandas as pd
import requests
import json
import random
import uuid
from src.database import get_connection, reset_db

# --- CONFIGURATION ---
STATE = "36"   # NY
COUNTY = "045" # Jefferson

# 1. GEOGRAPHY: TIGERweb Current -> Layer 8 (Census Tracts)
#
TIGER_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/8/query"

# 2. DEMOGRAPHICS: ACS 5-Year Profile
#
ACS_URL = "https://api.census.gov/data/2023/acs/acs5/profile"

def fetch_real_tracts():
    print(f"🌍 Fetching Tracts from TIGERweb (Layer 8)...")
    params = {
        "where": f"STATE='{STATE}' AND COUNTY='{COUNTY}'",
        "outFields": "GEOID,NAME",
        "f": "geojson"
    }
    
    try:
        resp = requests.get(TIGER_URL, params=params, timeout=15)
        data = resp.json()
        
        cleaned = []
        for f in data.get('features', []):
            props = f.get('properties', {})
            geoid = props.get('GEOID')
            
            # STRICT VALIDATION: Tracts MUST be 11 digits
            if geoid and len(geoid) == 11:
                cleaned.append({
                    'geoid': geoid,
                    'name': props.get('NAME'), 
                    'geometry': json.dumps(f.get('geometry'))
                })
        
        print(f"✅ Retrieved {len(cleaned)} Valid Tracts.")
        return cleaned
    except Exception as e:
        print(f"❌ Geo Fetch Error: {e}")
        return []

def fetch_real_demographics():
    print("📊 Fetching Demographics from ACS...")
    # DP05_0001E=Total, DP05_0019E=<18, DP05_0024E=65+
    # DP05_0037E=White, DP05_0038E=Black, DP05_0071E=Hispanic
    params = {
        "get": "DP05_0001E,DP05_0019E,DP05_0024E,DP05_0037E,DP05_0038E,DP05_0071E",
        "for": "tract:*",
        "in": f"state:{STATE} county:{COUNTY}"
    }
    
    try:
        resp = requests.get(ACS_URL, params=params, timeout=10)
        rows = resp.json()
        
        demo_map = {}
        for r in rows[1:]: # Skip header
            # ACS returns GEOID parts separately (State, County, Tract)
            # We must concatenate them to match TIGERweb GEOID
            geoid = r[-3] + r[-2] + r[-1]
            
            total = int(r[0]) if r[0] else 0
            if total == 0: continue
            
            def safe_pct(n, d): return round((int(n or 0)/d)*100, 1)
            
            demo_map[geoid] = {
                "total_pop": total,
                "pct_under_18": safe_pct(r[1], total),
                "pct_senior": safe_pct(r[2], total),
                "pct_white": safe_pct(r[3], total),
                "pct_black": safe_pct(r[4], total),
                "pct_hispanic": safe_pct(r[5], total)
            }
        return demo_map
    except Exception as e:
        print(f"❌ ACS Fetch Error: {e}")
        return {}
    
def load_svi_from_csv(csv_path="data/svi_jefferson.csv"):
    """
    Loads SVI data. Expects columns: 'FIPS' (GEOID) and 'RPL_THEMES' (Overall SVI).
    Returns dict: {'36045...': 0.85, ...}
    """
    print(f"📄 Loading SVI data from {csv_path}...")
    try:
        # dtype={'FIPS': str} preserves leading zeros
        df = pd.read_csv(csv_path, dtype={'FIPS': str})
        
        # Normalize columns if needed (Example: Standard CDC names)
        # If your CSV uses different names, rename them here
        if 'FIPS' not in df.columns:
            # Fallback: try to find a column that looks like a GEOID
            possible_cols = [c for c in df.columns if 'GEO' in c.upper() or 'FIPS' in c.upper()]
            if possible_cols:
                df = df.rename(columns={possible_cols[0]: 'FIPS'})
        
        # Create lookup dict
        svi_map = df.set_index('FIPS')['RPL_THEMES'].to_dict()
        print(f"✅ Loaded {len(svi_map)} SVI records.")
        return svi_map
    except Exception as e:
        print(f"⚠️ CSV Load Failed: {e}. Falling back to simulation.")
        return {}
    


def run_simulation():

    reset_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Fetch External Data
    tracts = fetch_real_tracts()
    demos = fetch_real_demographics()
    
    # NEW: Load the CSV (Ensure you put the file in the right folder!)
    real_svi_data = load_svi_from_csv(".\data\svi_interactive_map.csv")
    
    if not tracts:
        print("⚠️ No tracts found. Aborting.")
        return

    # 2. Populate DB
    print("🎲 Running Hybrid Simulation...")
    tract_ids = []
    
    for t in tracts:
        tid = t['geoid']
        
        # MERGE: Look up demographics by GEOID
        # If ACS failed or mismatch, fall back to dummy data
        d = demos.get(tid, {
            "total_pop": 1000, "pct_under_18": 20, "pct_senior": 15,
            "pct_white": 80, "pct_black": 5, "pct_hispanic": 5
        })
        
       # --- NEW SVI LOGIC ---
        if tid in real_svi_data:
            # Use the REAL value
            svi = real_svi_data[tid]
            # Handle -999 (CDC code for missing data)
            if svi < 0: svi = 0.5 
        else:
            # Fallback only if missing from CSV
            is_urban = tid.startswith("3604506")
            svi = round(random.uniform(0.5, 0.95), 2) if is_urban else round(random.uniform(0.1, 0.6), 2)
        
        cursor.execute(
            "INSERT INTO raw_tracts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (tid, f"Tract {t['name']}", t['geometry'], svi, 0.0, 0.0, 0.0, json.dumps(d))
        )
        tract_ids.append((tid, svi))

    # 3. Simulate Assets (Capacity)
    assets_types = ['Library', 'School', 'Community Center', 'Park', 'Clinic']
    for tid, svi in tract_ids:
        # High Need (SVI) = High Risk of 'Desert' (Fewer Assets)
        weights = [svi*6, svi*3, (1-svi)*2, (1-svi)*4]
        num_assets = random.choices([0, 1, 2, 4], weights=weights, k=1)[0]
        
        for _ in range(num_assets):
            cursor.execute("INSERT INTO raw_assets VALUES (?, ?, ?)",
                (str(uuid.uuid4()), tid, random.choice(assets_types)))

    conn.commit()
    count = cursor.execute("SELECT count(*) FROM raw_tracts").fetchone()[0]
    conn.close()
    print(f"🚀 SUCCESS: Database populated with {count} real tracts.")

if __name__ == "__main__":
    run_simulation()