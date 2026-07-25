import os
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI(title="Eco-Loop Building Optimization Dashboard API")

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
BASE_HTML_DIR = os.path.abspath(os.path.dirname(__file__))

@app.get("/")
def get_dashboard():
    return FileResponse(os.path.join(BASE_HTML_DIR, "index.html"))

@app.get("/api/metrics")
def get_metrics():
    baseline_path = os.path.join(DATA_DIR, "baseline_telemetry.csv")
    ai_path = os.path.join(DATA_DIR, "ai_telemetry.csv")
    
    if not os.path.exists(baseline_path) or not os.path.exists(ai_path):
        return {"error": "Telemetry data files not found. Run baseline and closed-loop scripts first."}
        
    df_base = pd.read_csv(baseline_path)
    df_ai = pd.read_csv(ai_path)
    
    # Calculate energy totals (Convert Joules to kWh: J / 3,600,000)
    # The columns may contain values for every timestep
    total_joules_base = df_base["FacilityPower"].sum()
    total_joules_ai = df_ai["FacilityPower"].sum()
    
    kwh_base = total_joules_base / 3600000.0
    kwh_ai = total_joules_ai / 3600000.0
    savings_pct = ((kwh_base - kwh_ai) / kwh_base * 100.0) if kwh_base > 0 else 0.0
    
    # Format time index for plotting
    df_base["Timestamp"] = df_base["Month"].astype(str) + "/" + df_base["Day"].astype(str) + " " + df_base["Hour"].astype(str).str.zfill(2) + ":" + df_base["Minute"].astype(str).str.zfill(2)
    df_ai["Timestamp"] = df_ai["Month"].astype(str) + "/" + df_ai["Day"].astype(str) + " " + df_ai["Hour"].astype(str).str.zfill(2) + ":" + df_ai["Minute"].astype(str).str.zfill(2)
    
    # Decimate dataset to 100 steps for clean chart rendering
    decimation_factor = max(1, len(df_base) // 100)
    chart_base = df_base.iloc[::decimation_factor].to_dict(orient="records")
    chart_ai = df_ai.iloc[::decimation_factor].to_dict(orient="records")
    
    # Calculate average PMV and comfort violations (PMV outside -0.7 to +0.7 range)
    avg_pmv_base = float(df_base["PMV"].mean())
    avg_pmv_ai = float(df_ai["PMV"].mean())
    
    # PMV bounds violation checks
    violations_base = int((df_base["PMV"] < -0.7).sum() + (df_base["PMV"] > 0.7).sum())
    violations_ai = int((df_ai["PMV"] < -0.7).sum() + (df_ai["PMV"] > 0.7).sum())
    
    return {
        "totals": {
            "kwh_baseline": round(kwh_base, 2),
            "kwh_optimized": round(kwh_ai, 2),
            "savings_percentage": round(savings_pct, 2),
            "avg_pmv_baseline": round(avg_pmv_base, 3),
            "avg_pmv_optimized": round(avg_pmv_ai, 3),
            "violations_baseline": violations_base,
            "violations_optimized": violations_ai
        },
        "chart_data": {
            "baseline": chart_base,
            "optimized": chart_ai
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
