# 🍃 Eco-Loop Building Optimization Agents

Eco-Loop is a Physics-informed Autonomous Building Management Supervisory Agent. Built for the Honeywell Hackathon, it bridges advanced open-source Cognitive LLMs with high-fidelity physics simulators (EnergyPlus) to achieve closed-loop supervisory control over HVAC setpoints—realizing significant energy savings without compromising human occupant comfort.

---

## 🚀 Key Achievements

* **18.48% Total HVAC Electricity Reduction** (Chicago winter weather conditions, 1-week timeline).
* **0 Comfort Violations**: Dynamically adjusted thermostat variables while strictly maintaining occupant PMV comfort between ASHRAE-approved thresholds (-0.7 to +0.7).
* **Fully Closed-Loop Autonomous Pipeline**: No human code modifications required during active execution runtime.

---

## 🛠️ Project Structure

* `simulation/`
  * `building.idf`: The 5-Zone office building physical layout model containing zone envelope properties and thermal setpoints.
  * `weather.epw`: Climate data for Chicago, IL used for boundary load profiles.
  * `closed_loop.py`: The live feedback simulation runner containing actuator registers and LLM decision hooks.
  * `runner.py`: Baseline sandbox runner for unoptimized profiling benchmarks.
* `agent/`
  * `agent_loop.py`: Orchestrates tools, context structure, and calls the Groq-hosted open-source model.
  * `mcp_server.py`: Model Context Protocol Server JSON-RPC bridge containing tools for telemetry retrieval and thermostat actuation. Exposes interactive web-based tools dashboard at `/tools` and Swagger docs at `/docs` with light theme optimization.
* `dashboard/`
  * `server.py`: FastAPI backend parsing simulation database logs and exposing comparative JSON metrics.
  * `index.html`: Responsive, light-mode dashboard comparing baseline vs optimized performance curves.

---

## ⚙️ Fast Setup & Run

### 1. Requirements & Dependencies
Make sure [EnergyPlus](https://energyplus.net/downloads) (tested on 26.1) is installed inside your `/Applications` directory.

Set up your virtual environment and install libraries:
```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pandas requests jinja2
```

Configure your Groq API Key environment variable:
```bash
export GROQ_API_KEY="your_groq_api_key_here"
```


### 2. Running Simulations
Run the unoptimized baseline simulation:
```bash
python simulation/runner.py
```

Run the closed-loop optimization (uses Groq LLM API client):
```bash
python simulation/closed_loop.py
```

### 3. Launching the Servers & Dashboards
Launch the performance monitoring dashboard (runs on port 8000):
```bash
python dashboard/server.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

Launch the MCP Server (runs on port 8001):
```bash
python agent/mcp_server.py
```
Open **[http://localhost:8001](http://localhost:8001)** in your browser to view the root hub, the interactive **MCP Tools testing panel** at `/tools`, or the interactive **API Documentation** at `/docs`.

---

## 🎛️ Real Building Ingestion (BACnet/BMS Bridge)

To transition this PoC from the EnergyPlus simulator sandbox to a live building, swap the simulation data-exchange calls for physical building protocol drivers (e.g. BACnet IP / MSTP):

```
+--------------------+         BACnet/IP          +--------------------------+
| Physical BMS       | <========================> | BACnet Gateway Client    |
| (Thermostats, AHU) |    (Read/Write Commands)   | (e.g., using BAC0)       |
+--------------------+                            +------------+-------------+
                                                               |
                                                               | (Telemetry JSON)
                                                               v
+--------------------+        Apply Overrides     +--------------------------+
| HVAC Actuators /   | <========================> | Eco-Loop MCP Server      |
| Setpoint Registers |        (BACnet Write)      | (agent/mcp_server.py)    |
+--------------------+                            +--------------------------+
```

### Transition Roadmap:
1. **Telemetry Ingestion**: Instead of parsing the local `telemetry.csv` file, the `/tools/get_building_telemetry` tool queries active BACnet points:
   ```python
   import BAC0
   bacnet = BAC0.connect(ip="192.168.1.100")
   zone_temp = bacnet.read("1:Analog Input, 1") # Physical Zone Sensor
   ```
2. **Control Execution**: In the `/tools/apply_control_action` tool, redirect setpoint actuators to BMS analog write objects:
   ```python
   bacnet.write("1:Analog Value, 5", action.heating_setpoint) # Thermostat Heat register
   ```

