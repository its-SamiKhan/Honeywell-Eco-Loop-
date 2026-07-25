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
* `dashboard/`
  * `server.py`: FastAPI backend parsing simulation database logs and exposing comparative JSON metrics.
  * `index.html`: Responsive, vibrant dark-mode dashboard comparing baseline vs optimized performance curves.

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

### 2. Running Simulations
Run the unoptimized baseline simulation:
```bash
python simulation/runner.py
```

Run the closed-loop optimization (uses Groq LLM API client):
```bash
python simulation/closed_loop.py
```

### 3. Launching the Web Dashboard
```bash
python dashboard/server.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.
