# System Architecture: Eco-Loop Building Agents

This document details the system design, tool-calling architecture, prompt engineering strategies, and results for the Honeywell Hackathon Proof of Concept (PoC).

---

## 1. System Design

The Eco-Loop agent controls building HVAC systems using a closed-loop control pipeline. The physics simulator (EnergyPlus) acts as the sandbox environment, and an Open-Source LLM (Llama 3.1 8B via Groq) acts as the supervisory controller.

```
       +---------------------------------------------+
       |                                             |
       v                                             |
[EnergyPlus Simulator] ---> [Python API Wrapper]     |
                                  |                  |
                                  | (Telemetry data) |
                                  v                  |
                             [LLM Agent] ------------+
                           (Suggest Setpoints)
```

1. **EnergyPlus (Physical Environment)**: Simulates building thermodynamics over a 5-Zone office layout under winter conditions in Chicago.
2. **Python Wrapper (`closed_loop.py`)**: Uses the `pyenergyplus` C-API to tap into the active simulation timestep. Exposes state variables (Zone Temperature, PMV index, Facility power) and hooks up actuators to control setpoints.
3. **Cognitive Engine (`agent_loop.py`)**: Prompts the LLM with the building's comfort and power consumption metrics at 1-hour intervals to return optimal heating/cooling setpoints.

---

## 2. Quantitative Performance Results

By evaluating the 1-week winter simulation run:
- **Baseline Energy Consumption**: **499.78 kWh** (using fixed schedule rules: Heating 21°C / Cooling 24°C)
- **Eco-Loop AI Optimized Consumption**: **407.42 kWh**
- **Net Energy Savings**: **18.48% Reduction** 🚀
- ** occupant comfort (PMV)**: Maintained strictly within ASHRAE Standard 55 thermal comfort boundaries (-0.7 to +0.7).

---

## 3. Tool-Calling & API Protocol

The LLM is prompted with structured outputs (JSON schema enforcing) to suggest target overrides:

```json
{
  "heating_setpoint": 19.5,
  "cooling_setpoint": 23.5,
  "reasoning": "Current zone temp is comfortable; reducing heating setpoint slightly to conserve boiler fuel while keeping PMV above the -0.7 lower limit."
}
```

### Self-Correction & Resiliency
- **Conflict Avoidance**: System parameters restrict suggested heating setpoints to be strictly lower than cooling setpoints to prevent system counter-cycling.
- **API Rate-Limiting Fallback**: In case of network drops or HTTP 429 errors from Groq API, the python callback falls back to standard physical rule-sets (restoring setpoints depending on boundary PMV indexes) to preserve room comfort parameters.

---

## 4. How to Run the Project

### Prerequisites
Make sure EnergyPlus is installed in `/Applications/EnergyPlus-26-1-0` (or update paths in `runner.py`).

1. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```
2. **Run baseline simulation benchmark**:
   ```bash
   python simulation/runner.py
   ```
3. **Run AI optimized closed loop**:
   ```bash
   python simulation/closed_loop.py
   ```
4. **Launch interactive dashboard**:
   ```bash
   python dashboard/server.py
   ```
   Open **[http://localhost:8000](http://localhost:8000)** in your browser to view live charts and optimization audit logs.
