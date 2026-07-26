import os
import json
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel

# Initialize a FastAPI app acting as the MCP Server (Model Context Protocol) JSON-RPC bridge
app = FastAPI(title="Eco-Loop Building MCP Server", description="Model Context Protocol Server for HVAC Closed-Loop Optimization", docs_url=None)

@app.get("/", response_class=HTMLResponse)
def root_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Eco-Loop MCP Server</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
        <style>
            body {
                margin: 0;
                padding: 0;
                font-family: 'Outfit', sans-serif;
                background: #fafafa;
                color: #3b4151;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                overflow: hidden;
            }
            .container {
                text-align: center;
                background: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 24px;
                padding: 3rem;
                max-width: 600px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
                animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1);
            }
            h1 {
                font-size: 2.5rem;
                font-weight: 800;
                margin-bottom: 0.5rem;
                color: #3b4151;
            }
            p {
                color: #6b7280;
                font-size: 1.1rem;
                margin-bottom: 2.5rem;
            }
            .grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1.5rem;
            }
            .card {
                text-decoration: none;
                background: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 16px;
                padding: 1.5rem;
                transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
                display: flex;
                flex-direction: column;
                align-items: center;
                cursor: pointer;
            }
            .card:hover {
                transform: translateY(-5px);
                background: rgba(59, 130, 246, 0.05);
                border-color: rgba(59, 130, 246, 0.3);
                box-shadow: 0 10px 20px rgba(59, 130, 246, 0.1);
            }
            .card-icon {
                font-size: 2rem;
                margin-bottom: 1rem;
            }
            .card-title {
                font-size: 1.2rem;
                font-weight: 600;
                color: #3b4151;
                margin-bottom: 0.5rem;
            }
            .card-desc {
                font-size: 0.9rem;
                color: #6b7280;
                line-height: 1.4;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div style="font-size: 3rem; margin-bottom: 1rem;">⚡</div>
            <h1>Eco-Loop MCP Server</h1>
            <p>Model Context Protocol Server for HVAC Closed-Loop Optimization</p>
            
            <div class="grid">
                <a href="/docs" class="card">
                    <div class="card-icon">📖</div>
                    <div class="card-title">Swagger UI</div>
                    <div class="card-desc">Interactive API docs to test endpoints.</div>
                </a>
                <a href="/tools" class="card">
                    <div class="card-icon">🛠️</div>
                    <div class="card-title">MCP Tools</div>
                    <div class="card-desc">List available model context protocol tools.</div>
                </a>
            </div>
        </div>
    </body>
    </html>
    """

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

class ControlAction(BaseModel):
    heating_setpoint: float
    cooling_setpoint: float
    reasoning: str

@app.get("/tools")
def list_tools(request: Request):
    """
    MCP Protocol: Exposes available tools to the supervisor LLM Client.
    Returns HTML UI for web browsers and JSON for MCP API clients.
    """
    tools_data = {
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
    
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Eco-Loop MCP Tools</title>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    font-family: 'Outfit', sans-serif;
                    background: #fafafa;
                    color: #3b4151;
                    min-height: 100vh;
                }
                .navbar {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 1.5rem 2rem;
                    background: #ffffff;
                    border-bottom: 1px solid #e8e8e8;
                }
                .nav-brand {
                    font-weight: 800;
                    font-size: 1.2rem;
                    text-decoration: none;
                    color: #3b4151;
                }
                .nav-link {
                    text-decoration: none;
                    color: #6b7280;
                    font-weight: 500;
                    transition: color 0.2s;
                }
                .nav-link:hover {
                    color: #3b82f6;
                }
                .container {
                    max-width: 900px;
                    margin: 3rem auto;
                    padding: 0 1.5rem;
                }
                h1 {
                    font-size: 2.2rem;
                    font-weight: 800;
                    margin-bottom: 2rem;
                    color: #3b4151;
                }
                .tool-card {
                    background: #ffffff;
                    border: 1px solid #e8e8e8;
                    border-radius: 20px;
                    padding: 2rem;
                    margin-bottom: 2rem;
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
                    transition: border-color 0.3s;
                }
                .tool-card:hover {
                    border-color: rgba(59, 130, 246, 0.3);
                }
                .tool-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 1rem;
                }
                .tool-name {
                    font-size: 1.5rem;
                    font-weight: 600;
                    color: #3b82f6;
                }
                .tool-method {
                    background: rgba(59, 130, 246, 0.1);
                    color: #3b82f6;
                    padding: 0.3rem 0.8rem;
                    border-radius: 8px;
                    font-size: 0.8rem;
                    font-weight: 600;
                }
                .tool-desc {
                    color: #6b7280;
                    line-height: 1.6;
                    margin-bottom: 1.5rem;
                }
                .section-title {
                    font-size: 1rem;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    color: #6b7280;
                    margin-bottom: 0.75rem;
                    font-weight: 600;
                }
                .params-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 1.5rem;
                }
                .params-table th, .params-table td {
                    text-align: left;
                    padding: 0.75rem;
                    border-bottom: 1px solid #e8e8e8;
                }
                .params-table th {
                    color: #6b7280;
                    font-weight: 500;
                    font-size: 0.9rem;
                }
                .param-name {
                    color: #3b4151;
                    font-family: monospace;
                    font-size: 0.95rem;
                }
                .param-type {
                    color: #c2410c;
                    font-family: monospace;
                    font-size: 0.85rem;
                }
                .param-desc {
                    color: #6b7280;
                }
                .btn-test {
                    background: #3b82f6;
                    border: none;
                    color: #ffffff;
                    padding: 0.75rem 1.5rem;
                    border-radius: 12px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .btn-test:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
                }
                .test-panel {
                    margin-top: 1.5rem;
                    padding: 1.5rem;
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    display: none;
                }
                .test-input-group {
                    margin-bottom: 1rem;
                }
                .test-label {
                    display: block;
                    margin-bottom: 0.5rem;
                    color: #3b4151;
                }
                .test-input {
                    width: 100%;
                    padding: 0.75rem;
                    background: #ffffff;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    color: #3b4151;
                    font-family: 'Outfit', sans-serif;
                    box-sizing: border-box;
                }
                .test-input:focus {
                    outline: none;
                    border-color: #3b82f6;
                }
                .test-result {
                    margin-top: 1rem;
                    padding: 1rem;
                    background: #f1f5f9;
                    border-radius: 8px;
                    font-family: monospace;
                    font-size: 0.9rem;
                    white-space: pre-wrap;
                    color: #0f172a;
                    border: 1px solid #cbd5e1;
                    display: none;
                }
            </style>
        </head>
        <body>
            <div class="navbar">
                <a href="/" class="nav-brand">⚡ Eco-Loop MCP</a>
                <a href="/" class="nav-link">← Back to Hub</a>
            </div>
            <div class="container">
                <h1>Available Model Context Protocol (MCP) Tools</h1>
                
                <!-- Tool 1 -->
                <div class="tool-card">
                    <div class="tool-header">
                        <div class="tool-name">get_building_telemetry</div>
                        <div class="tool-method">POST /tools/get_building_telemetry</div>
                    </div>
                    <div class="tool-desc">Reads current building temperature, outdoor weather, PMV comfort indexes, and current electricity usage from the simulation.</div>
                    
                    <div class="section-title">Parameters</div>
                    <p style="color: #9ca3af; font-size: 0.95rem; margin-bottom: 1.5rem;">None required.</p>
                    
                    <button class="btn-test" onclick="toggleTest('telemetry-panel')">Test Tool</button>
                    
                    <div id="telemetry-panel" class="test-panel">
                        <button class="btn-test" onclick="runTelemetryTest()">Send Request</button>
                        <div id="telemetry-result" class="test-result"></div>
                    </div>
                </div>

                <!-- Tool 2 -->
                <div class="tool-card">
                    <div class="tool-header">
                        <div class="tool-name">apply_control_action</div>
                        <div class="tool-method">POST /tools/apply_control_action</div>
                    </div>
                    <div class="tool-desc">Applies supervisory thermostat override control actions to the building simulation. Safely validates cooling vs heating setpoints.</div>
                    
                    <div class="section-title">Parameters</div>
                    <table class="params-table">
                        <thead>
                            <tr>
                                <th>Parameter</th>
                                <th>Type</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td class="param-name">heating_setpoint</td>
                                <td class="param-type">float</td>
                                <td class="param-desc">Target heating setpoint in Celsius (e.g. 18.0 - 22.0)</td>
                            </tr>
                            <tr>
                                <td class="param-name">cooling_setpoint</td>
                                <td class="param-type">float</td>
                                <td class="param-desc">Target cooling setpoint in Celsius (e.g. 22.0 - 26.0)</td>
                            </tr>
                            <tr>
                                <td class="param-name">reasoning</td>
                                <td class="param-type">string</td>
                                <td class="param-desc">Justification reasoning for the suggested overrides.</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <button class="btn-test" onclick="toggleTest('control-panel')">Test Tool</button>
                    
                    <div id="control-panel" class="test-panel">
                        <div class="test-input-group">
                            <label class="test-label">Heating Setpoint (°C)</label>
                            <input type="number" step="0.1" id="heat-input" class="test-input" value="20.0">
                        </div>
                        <div class="test-input-group">
                            <label class="test-label">Cooling Setpoint (°C)</label>
                            <input type="number" step="0.1" id="cool-input" class="test-input" value="24.0">
                        </div>
                        <div class="test-input-group">
                            <label class="test-label">Reasoning</label>
                            <input type="text" id="reasoning-input" class="test-input" value="Optimizing comfort vs power based on outdoor temperature.">
                        </div>
                        <button class="btn-test" onclick="runControlTest()">Send Action</button>
                        <div id="control-result" class="test-result"></div>
                    </div>
                </div>
            </div>

            <script>
                function toggleTest(id) {
                    const panel = document.getElementById(id);
                    if (panel.style.display === 'block') {
                        panel.style.display = 'none';
                    } else {
                        panel.style.display = 'block';
                    }
                }

                async function runTelemetryTest() {
                    const resultDiv = document.getElementById('telemetry-result');
                    resultDiv.style.display = 'block';
                    resultDiv.innerText = 'Loading...';
                    try {
                        const response = await fetch('/tools/get_building_telemetry', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' }
                        });
                        const data = await response.json();
                        resultDiv.innerText = JSON.stringify(data, null, 2);
                    } catch (err) {
                        resultDiv.innerText = 'Error: ' + err.message;
                    }
                }

                async function runControlTest() {
                    const resultDiv = document.getElementById('control-result');
                    resultDiv.style.display = 'block';
                    resultDiv.innerText = 'Loading...';
                    
                    const heating = parseFloat(document.getElementById('heat-input').value);
                    const cooling = parseFloat(document.getElementById('cool-input').value);
                    const reasoning = document.getElementById('reasoning-input').value;

                    try {
                        const response = await fetch('/tools/apply_control_action', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                heating_setpoint: heating,
                                cooling_setpoint: cooling,
                                reasoning: reasoning
                            })
                        });
                        const data = await response.json();
                        resultDiv.innerText = JSON.stringify(data, null, 2);
                        if (data.status === 'rejected') {
                            resultDiv.style.color = '#f87171';
                            resultDiv.style.borderColor = 'rgba(248, 113, 113, 0.2)';
                        } else {
                            resultDiv.style.color = '#34d399';
                            resultDiv.style.borderColor = 'rgba(52, 211, 153, 0.2)';
                        }
                    } catch (err) {
                        resultDiv.innerText = 'Error: ' + err.message;
                        resultDiv.style.color = '#f87171';
                    }
                }
            </script>
        </body>
        </html>
        """)
    return tools_data

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

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    response = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Eco-Loop Building MCP Server - Swagger UI",
    )
    html_content = response.body.decode("utf-8")
    custom_header = """
    <div style="background: #ffffff; border-bottom: 1px solid #e2e8f0; padding: 0.8rem 2.5rem; display: flex; justify-content: space-between; align-items: center; font-family: 'Outfit', -apple-system, sans-serif; height: 55px; box-sizing: border-box; position: sticky; top: 0; z-index: 9999;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-weight: 800; font-size: 1.1rem; color: #3b4151;">⚡ Eco-Loop MCP</span>
            <span style="color: #cbd5e1; font-weight: 300;">|</span>
            <span style="color: #64748b; font-size: 0.9rem; font-weight: 500;">Swagger API Interactive Documentation</span>
        </div>
        <a href="/" style="text-decoration: none; color: #3b82f6; font-weight: 600; font-size: 0.9rem; padding: 0.4rem 0.8rem; border-radius: 6px; transition: all 0.2s;" onmouseover="this.style.background='rgba(59, 130, 246, 0.05)'" onmouseout="this.style.background='transparent'">← Back to Hub</a>
    </div>
    """
    html_content = html_content.replace("<body>", f"<body>{custom_header}")
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    # Runs the MCP Server locally on port 8001
    uvicorn.run(app, host="0.0.0.0", port=8001)
