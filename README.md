# 🎯 Tug Hill Regional Grantmaker (Proof of Concept)

A data-driven decision support tool designed to identify "Grant Deserts" in the Tug Hill / North Country region. This application correlates **Social Vulnerability (SVI)** with **Non-Profit Capacity** to prioritize funding allocation.

![Status](https://img.shields.io/badge/Status-Prototype-orange) ![Python](https://img.shields.io/badge/Python-3.9+-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red)

## ⚠️ Disclaimer

### Personal Project / Non-Affiliation
* **Capacity:** This project is a personal portfolio piece created in a private capacity. It is **not** associated with, endorsed by, or funded by any employer (past or present). It is not the basis of any decisions made by any current employer.
* **Data Sources:** This tool uses **Real Geography** (Census TIGERweb API), **Real Demographics** (ACS 5-Year Profile), and **Real SVI Scores** (CDC Interactive Map). However, the **Asset Locations are currently SIMULATED** for demonstration purposes. 
* **Privacy:** No private, confidential, or proprietary data sources were used in the creation of this product.
* **Usage:** For illustrative purposes only. Do not use for official financial or health-equity decision-making.

## 🗺️ How It Works

The application moves beyond simple "Need" maps by introducing a **Feasibility Score**:

1. **The Need (SVI):** Identifies census tracts with high social vulnerability.
2. **The Capacity (Assets):** Maps existing infrastructure (libraries, schools, clinics).
3. **The Strategy:**
    * 🔴 **Urgent Desert:** High Need + Low Capacity $\rightarrow$ *Strategy: Capacity Building Grants*
    * 🟢 **High-Capacity Hub:** High Need + High Capacity $\rightarrow$ *Strategy: Program Innovation Grants*

## 💡 Development Methodology

**Objective:** Rapidly validate a data-driven hypothesis ("Grant Deserts") before committing to expensive engineering hours.

* **Rapid Prototyping:** Leveraged a "Human-in-the-Loop" AI workflow to accelerate boilerplate code generation (ETL pipelines, UI scaffolding), reducing development time from weeks to days.
* **Architecture:** Chosen for velocity and portability. Uses **Streamlit** for instant frontend interactivity and **SQLite** for a serverless, self-contained data layer.
* **Validation:** While AI accelerated the code, all business logic, SVI thresholding parameters, and data integrity checks were architected and verified manually to ensure domain accuracy.

## 🚀 Quick Start

### 1. Installation

```bash
git clone [https://github.com/blowerd/tug-hill-grantmaker.git](https://github.com/blowerd/tug-hill-grantmaker.git)
cd tug-hill-grantmaker
pip install -r requirements.txt
```

### 2. Data Generation (Hybrid Simulation -- Optional)

The repo comes with a utility script to build the local database. This step fetches real Census Tract boundaries for Jefferson, Lewis, and St. Lawrence Counties, merges them with CDC SVI data, and instantiates simulated assets for the demo.

```bash
# Run as a module to handle relative imports correctly
python -m src.etl
```

### 3. Run the App

```bash
streamlit run app.py
```

### 📂 Project Structure

* app.py: The Streamlit frontend. Handles the Map (PyDeck), Sidebar, and Drill-Down logic.
* src/database.py: Schema definition. Contains the vw_tract_profile SQL View which handles the scoring logic.
* src/etl.py: The ETL pipeline. Fetches real Census GeoJSON/ACS data, preloads the local svi data, and merges it with the scoring model.

### 🛠️ Data Sources

* Geography: US Census Bureau TIGERweb (WMS Layer 8 - Census Tracts)
* Demographics: US Census Bureau ACS 5-Year Data Profile (DP05)
* SVI: CDC SVI Interactive Map (2022 Vintage)
  
### 🔮 Roadmap & Future Features

While this project is a finalized Proof of Concept, the following features would be required for a production deployment:

* Real Asset Tracking: Integration of IRS Form 990 data to replace simulated asset points with real non-profit locations.
* Infrastructure: Migration from SQLite to DuckDB for analytical performance, and Dockerization for cloud or local deployment.
* Granular Data: Incorporation of county-wide economic statistics and local "Food Access" or "Housing Trends" indices.
* Scenario Modeling: Development of "what if" tools to simulate how demographic shifts might impact funding priorities over 5-10 years.
* User Layering: Adopt the app to accept local/custom files for further integration and analysis.
* Tug Hill Specifics: Ingestion of annual survey data provided by the Center for Community Studies for longitudinal trending.

## 🤖 Generative AI Usage Disclosure

Generative AI (Gemini) was leveraged for documentation drafting and boilerplate code generation (Census API fetching, GUI scaffolding). All outputs were validated, refactored, and integrated by the human developer.
