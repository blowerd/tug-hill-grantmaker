import sqlite3
from sqlite3 import Connection
import os
from pathlib import Path

# --- THE FIX: ABSOLUTE PATHING ---
# Find the 'src' directory
BASE_DIR = Path(__file__).resolve().parent.parent 
# Force DB to live in the Project Root, always.
DB_PATH = BASE_DIR / "grant_maker.db"

def get_connection() -> Connection:
    # Connect to the absolute path
    conn = sqlite3.connect(str(DB_PATH)) 
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # ... (Rest of your SQL schema remains exactly the same) ...
    # ... Copy/Paste your existing table/view definitions here ...
    
    # --- RAW TABLES ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_tracts (
            tract_id TEXT PRIMARY KEY, 
            name TEXT, 
            geometry JSON, 
            overall_svi REAL, 
            housing_svi REAL, 
            poverty_rate REAL, 
            pop_density REAL,
            demographics_json JSON
        );
    """)
    # (Keep all other tables...)
    cursor.execute("CREATE TABLE IF NOT EXISTS raw_orgs (org_id TEXT PRIMARY KEY, name TEXT, budget INTEGER, years_operating INTEGER);")
    cursor.execute("CREATE TABLE IF NOT EXISTS raw_offices (office_id TEXT PRIMARY KEY, org_id TEXT, tract_id TEXT, office_type TEXT, FOREIGN KEY(org_id) REFERENCES raw_orgs(org_id));")
    cursor.execute("CREATE TABLE IF NOT EXISTS raw_assets (asset_id TEXT PRIMARY KEY, tract_id TEXT, type TEXT);")
    cursor.execute("CREATE TABLE IF NOT EXISTS raw_grants (grant_id TEXT PRIMARY KEY, org_id TEXT, amount INTEGER, status TEXT, theme TEXT);")
    cursor.execute("CREATE TABLE IF NOT EXISTS link_grant_area (link_id INTEGER PRIMARY KEY, grant_id TEXT, tract_id TEXT, pct_allocation REAL);")

    # --- REPORTING VIEW ---
    cursor.execute("DROP VIEW IF EXISTS vw_tract_profile")
    cursor.execute("""
    CREATE VIEW vw_tract_profile AS
    SELECT 
        t.tract_id, 
        t.name, 
        t.geometry, 
        t.overall_svi, 
        t.housing_svi,
        t.demographics_json,
        RANK() OVER (ORDER BY t.overall_svi DESC) as local_svi_rank,
        COUNT(DISTINCT a.asset_id) as count_assets,
        CASE 
            WHEN t.overall_svi > 0.75 AND COUNT(DISTINCT a.asset_id) < 2 THEN 'Urgent Desert'
            WHEN t.overall_svi > 0.75 AND COUNT(DISTINCT a.asset_id) >= 4 THEN 'High-Capacity Hub'
            WHEN t.overall_svi < 0.25 THEN 'Stable / Low Need'
            ELSE 'General Opportunity'
        END as context_tag
    FROM raw_tracts t
    LEFT JOIN raw_assets a ON t.tract_id = a.tract_id
    GROUP BY t.tract_id;
    """)

    conn.commit()
    conn.close()

def reset_db():
    # Delete the ABSOLUTE path file
    if DB_PATH.exists():
        os.remove(DB_PATH)
    init_db()