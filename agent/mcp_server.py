import os
import json
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

# Initialize a FastAPI app acting as the MCP Server (Model Context Protocol) JSON-RPC bridge
app = FastAPI(title="Eco-Loop Building MCP Server", description="Model Context Protocol Server for HVAC Closed-Loop Optimization")

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

class ControlAction(BaseModel):
    heating_setpoint: float
    cooling_setpoint: float
    reasoning: str

@app.get("/tools")
def list_tools():
    """
    MCP Protocol: Exposes available tools to the supervisor LLM Client.
    """
    return {
        "tools": [
            {
                "name": "get_building_telemetry",
                "description": "Reads current building temperature, outdoor weather, PMV comfort indexes, and current electricity usage.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "apply_control_action",
                "description": "Applies supervisory thermostat override control actions to the building simulation.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "heating_setpoint": {"type": "number", "description": "Target heating setpoint in Celsius (e.g. 18.0 - 22.0)"},
                        "cooling_setpoint": {"type": "number", "description": "Target cooling setpoint in Celsius (e.g. 22.0 - 26.0)"},
                        "reasoning": {"type": "string", "description": "Justification reasoning for the suggested setpoint overrides."}
                    },
                    "required": ["heating_setpoint", "cooling_setpoint", "reasoning"]
                }
            }
        ]
    }

@app.post("/tools/get_building_telemetry")
def get_building_telemetry():
    """
    MCP Tool Implementation: Fetches the latest live timestep telemetry row from the simulation metrics.
    """
    telemetry_path = os.path.join(DATA_DIR, "ai_telemetry.csv")
    if not os.path.exists(telemetry_path):
        # Fallback to baseline if loop hasn't generated metrics yet
        telemetry_path = os.path.join(DATA_DIR, "baseline_telemetry.csv")
        
    if not os.path.exists(telemetry_path):
        return {"status": "error", "message": "No active telemetry files found."}
        
    try:
        df = pd.read_csv(telemetry_path)
        last_row = df.iloc[-1].to_dict()
        return {
            "status": "success",
            "telemetry": {
                "month": int(last_row.get("Month", 1)),
                "day": int(last_row.get("Day", 1)),
                "hour": int(last_row.get("Hour", 0)),
                "minute": int(last_row.get("Minute", 0)),
                "outdoor_temp": float(last_row.get("OutdoorTemp", 0.0)),
                "zone_temp_space1_1": float(last_row.get("Temp_SPACE1-1", 20.0)),
                "pmv_comfort_index": float(last_row.get("PMV", 0.0)),
                "electricity_power_watts": float(last_row.get("FacilityPower", 0.0))
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/tools/apply_control_action")
def apply_control_action(action: ControlAction):
    """
    MCP Tool Implementation: Processes and registers LLM optimization setpoint controls.
    """
    # Interlocking safety validation check
    if action.cooling_setpoint <= action.heating_setpoint:
        return {
            "status": "rejected",
            "reason": "Interlock failure: Cooling setpoint must be strictly higher than heating setpoint to prevent counter-cycling."
        }
        
    print(f"[MCP Server Action Registered] Heat: {action.heating_setpoint}°C | Cool: {action.cooling_setpoint}°C | Reasoning: {action.reasoning}")
    return {
        "status": "applied",
        "heating_setpoint": action.heating_setpoint,
        "cooling_setpoint": action.cooling_setpoint
    }

if __name__ == "__main__":
    import uvicorn
    # Runs the MCP Server locally on port 8001
    uvicorn.run(app, host="0.0.0.0", port=8001)
