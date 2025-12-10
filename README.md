# 🎯 Tug Hill Regional Grantmaker (Proof of Concept)

A data-driven decision support tool designed to identify "Grant Deserts" in the Tug Hill region. This application correlates **Social Vulnerability (SVI)** with **Non-Profit Capacity** to prioritize funding allocation.

![Status](https://img.shields.io/badge/Status-Prototype-orange) ![Python](https://img.shields.io/badge/Python-3.9+-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red)

## ⚠️ Disclaimer

**Personal Project / Non-Affiliation**
* **Capacity:** This project is a personal portfolio piece created in a private capacity. It is **not** associated with, endorsed by, or funded by any employer. It is not also the basis of any decisions made by any employer.
* **Data Sources:** This tool uses **Real Geography** (Census TIGERweb API), **Real Demographics** (ACS 5-Year Profile), and **Real SVI Scores** (CDC Interactive Map). However, the **Asset Locations are currently SIMULATED** for demonstration purposes.
* **Usage:** For illustrative purposes only. Do not use for official financial and health-equity based decision-making.

## 🗺️ How It Works

The application moves beyond simple "Need" maps by introducing a **Feasibility Score**:

1. **The Need (SVI):** Identifies census tracts with high social vulnerability.
2. **The Capacity (Assets):** Maps existing infrastructure (libraries, schools, clinics).
3. **The Strategy:**
    * 🔴 **Urgent Desert:** High Need + Low Capacity $\rightarrow$ *Strategy: Capacity Building Grants*
    * 🟢 **High-Capacity Hub:** High Need + High Capacity $\rightarrow$ *Strategy: Program Innovation Grants*

## 🚀 Quick Start

### 1. Installation

```bash
git clone [https://github.com/your-username/tug-hill-grantmaker.git](https://github.com/your-username/tug-hill-grantmaker.git)
cd tug-hill-grantmaker
pip install -r requirements.txt
```

### 2. Data Generation (Hybrid Simulation -- Optional)

If needed or desired, there is a utility script for rerolling the database (simulation.py). This step fetches real Census Tract boundaries for Jefferson County, NY, and populates the SQLite database with simulated opportunity metrics based upon real SVI and demographic data.

### 3. Run the App

```bash
streamlit run app.py
```

### 📂 Project Structure

* app.py: The Streamlit frontend. Handles the Map (PyDeck), Sidebar, and Drill-Down logic.
* src/database.py: Schema definition. Contains the vw_tract_profile SQL View which handles the scoring logic.
* utils/simulation.py: The ETL pipeline. Fetches real Census GeoJSON and merges it with the scoring model.

### 🛠️ Data Sources

* Geography: US Census Bureau TIGERweb (WMS Layer 8 - Census Tracts)
* Demographics: US Census Bureau ACS 5-Year Data Profile (DP05)
* SVI: CDC SVI Interactive Map
