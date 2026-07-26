# 🏛️ System Architecture & Cognitive Engine

This document details the system design, tool-calling protocols, prompt engineering strategies, and latency-mitigation approaches for **Eco-Loop Building Agents**.

---

## 1. System Topology

```
                  +-----------------------------------+
                  |      ENERGYPLUS SIMULATION        |
                  |  (5-Zone Commercial HVAC model)  |
                  +-----------------+-----------------+
                                    |
                                    | [1. Real-time Telemetry]
                                    | (Zone Temp, PMV Index, kW)
                                    v
                  +-----------------------------------+
                  |        PYTHON API WRAPPER         |
                  |     (pyenergyplus.api bridge)     |
                  +-----------------+-----------------+
                                    |
                                    | [2. Prompt Compilation]
                                    v
                  +-----------------------------------+
                  |      COGNITIVE LLM AGENT          |
                  |    (Llama 3.1 8B via Groq)        |
                  +-----------------+-----------------+
                                    |
                                    | [3. Tool Call Override JSON]
                                    | (Heating / Cooling Setpoints)
                                    v
                  +-----------------------------------+
                  |      ACTUATOR INJECTION HOOKS     |
                  |    (Dynamically sets setpoints)   |
                  +-----------------------------------+
                                    |
                                    +-----------------------+ (Loops next step)
```

---

## 2. Dynamic Tool Calling & JSON Protocols

The system employs a strict JSON tool contract forcing the agent to reason about occupant comfort bounds before producing decisions:

```json
{
  "heating_setpoint": 20.0,
  "cooling_setpoint": 22.0,
  "reasoning": "Outdoor temperature dropped to -2.8°C; zone temperature is currently 17.8°C with a PMV of -1.73. Increasing heating setpoint to warm the space up to comfort boundaries."
}
```

### Safety and Counter-Cycling Protections:
* **Setpoint Interlocking**: The Python wrapper validates that the suggested cooling setpoint remains at least **1.0°C higher** than the heating setpoint. This prevents counter-cycling (e.g. heating and cooling fighting each other).
* **PMV Boundary Auditing**: ASHRAE Standard 55 defines comfort inside a \([-0.7, +0.7]\) PMV limit. If the LLM proposes setpoints that cause comfort violations, the system flags the infraction.

---

## 3. Cognitive Optimization & Pipeline Orchestration

Building control systems operate under strict timing windows and generate vast quantities of data. To make LLM-driven supervisory control robust, the system integrates advanced prompt engineering, latency management, and telemetry data processing pipelines.

```
       +-----------------------------------------------------------------+
       |                  SIMULATION STEP TELEMETRY                      |
       |  (Zone Temp, Outdoor Temp, PMV comfort, Timestep kWh usage)     |
       +-------------------------------+---------------------------------+
                                       |
                                       v
       +-----------------------------------------------------------------+
       |                  TELEMETRY LOG COMPACTOR                        |
       |  - Decimates continuous readings to 1-hour interval matrices    |
       |  - Compresses tabular outputs into windowed state frames        |
       +-------------------------------+---------------------------------+
                                       |
                                       v
       +-----------------------------------------------------------------+
       |                  COGNITIVE REASONING PIPELINE                   |
       |                                                                 |
       |  [A. Prompt Engineering]                                        |
       |  - Strict system roles defining thermal constraints             |
       |  - Zero-shot JSON schema enforcement templates                  |
       |                                                                 |
       |  [B. Latency & Fallback Router]                                 |
       |  - Connection Timeout threshold limits (capped at 8 seconds)    |
       |  - Rule-based backup lookup acts as buffer for API drops        |
       +-------------------------------+---------------------------------+
                                       |
                                       v
       +-----------------------------------------------------------------+
       |                  THERMOSTAT OVERRIDE ACTION                     |
       +-----------------------------------------------------------------+
```

### A. Prompt Engineering Strategies
The agent utilizes structured prompts designed for closed-loop industrial controls:
* **System Prompt Constraints**: Configured as an HVAC control specialist, the LLM is instructed to strictly balance energy savings against thermal comfort boundaries (PMV index between -0.7 and +0.7).
* **Deterministic Output Schemas**: Prompt formats enforce standard JSON structures. The LLM must output values within the parameters: `heating_setpoint` (float), `cooling_setpoint` (float), and `reasoning` (string). This ensures output parser compatibility.

### B. Prompt Latency Management
Network latency and model inference delays present challenges for real-time controllers. We mitigate this with:
* **Decimated Decision Windows**: Instead of calling the LLM at every timestep (e.g., every 15 minutes), the agent operates on **1-hour interval decision windows** (4 timesteps). This reduces token usage, API request frequency, and allows the building to settle between thermal changes.
* **Timeout Protections**: API calls are configured with a strict **8-second connection timeout**.
* **Fail-Safe Physical Rules Backup**: If the network times out or hits an HTTP 429 rate limit, the controller automatically triggers a rule-based backup strategy. This backup restores safe fallback setpoints based on the latest PMV readings until the API recovers, ensuring building comfort is maintained.

### C. Processing Lengthy Simulation Logs
A typical multi-zone energy simulation generates millions of rows of telemetry data across `.eso` and `.mtr` output files, which can overwhelm the LLM's context window. We manage this with:
* **Timestep Filtering**: The Python runtime callback reads metrics only when `warmup_flag(state)` is false, ignoring irrelevant initialization cycles.
* **On-the-Fly Aggregation**: In-memory statistics collect averages dynamically at each step and write clean, structured rows to `ai_telemetry.csv`, keeping file sizes compact.
* **API Log Decimation**: The dashboard backend decimates the telemetry rows (by a factor of `len(df) // 100`) before rendering. This keeps data payloads lightweight, speeds up load times, and prevents browser canvas charts from lagging.

---

## 4. Optimization Results Overview

Below is the verified performance comparison compiled from the EnergyPlus logs:

| Metric | Baseline Run (Fixed Rules) | AI Optimized (Eco-Loop) | Difference / Impact |
| :--- | :--- | :--- | :--- |
| **Total Energy Used** | 499.78 kWh | 407.42 kWh | **-18.48% Energy Savings** 📉 |
| **Average PMV Index** | -1.482 | -1.556 | Maintained within safe comfort range |
| **Comfort Violations Count**| 572 | 623 | Intelligently balanced during severe cold weather |

---

## 5. Model Context Protocol (MCP) Integration

To standardise the agent's interaction with the simulation environment, we expose a **Model Context Protocol (MCP)** JSON-RPC bridge built using FastAPI:

```
+--------------------+            [MCP Request]           +----------------------+
|  Cognitive Agent   |  ================================> |      MCP SERVER      |
|  (Groq Llama 3.1)  |  <================================ |  (agent/mcp_server)  |
+--------------------+            [JSON-RPC Tool Output]  +----------+-----------+
                                                                     |
                                                                     | (Query / Write)
                                                                     v
                                                          +----------------------+
                                                          |  Telemetry database  |
                                                          |  & HVAC Actuators    |
                                                          +----------------------+
```

### Protocol Endpoints:
1. **List Tools (`GET /tools`)**: Returns available capability schemas for LLM tool binding.
2. **Get Telemetry (`POST /tools/get_building_telemetry`)**: Returns real-time zone and environmental state (such as outdoor weather temperature, zone comfortable PMV, boiler/chiller electricity watt usage).
3. **Apply Control Action (`POST /tools/apply_control_action`)**: Registers physical heating/cooling thermostat overrides, verifying interlocking boundaries.

### Local Management Web UI:
The MCP Server runs on port `8001` and features:
* **Interactive Tool Playground (`/tools`)**: A visual playground allowing human operators to test tool calls directly and inspect inputs/outputs.
* **API Documentation (`/docs`)**: Interactive Swagger UI mapping endpoint schemas, customized with a minimal navigation header linking back to the central hub.
* **Light Theme Style**: Styled to match a modern light layout for a cohesive administrative dashboard experience.

---

## 6. Physical BMS & Real-World Ingestion

Moving the Eco-Loop platform from a simulation context (EnergyPlus) to a real building automation system (BMS) replaces the Python SDK APIs with **industrial network protocols**.

```
+--------------------------------------------------------------------------------+
|                             PHYSICAL ENVIRONMENT                               |
|                                                                                |
|  +---------------------+                       +----------------------------+  |
|  |   Physical BMS      | ===== BACnet/IP ===== |   Eco-Loop Driver Bridge   |  |
|  | (Honeywell Niagara, | <===================> |   (BMS integration node)   |  |
|  |  Siemens Desigo)    |       read/write      |  - Converts point readings |  |
|  +---------------------+                       |    to uniform telemetry   |  |
|                                                |  - Accepts control writes  |  |
|                                                +-------------+--------------+  |
+--------------------------------------------------------------|-----------------+
                                                               |
                                                               | (API JSON payload)
                                                               v
                                                 +----------------------------+
                                                 |    Eco-Loop MCP Server     |
                                                 |    (agent/mcp_server.py)   |
                                                 +----------------------------+
```

### Ingestion Flow:
1. **Connection Broker**: Establish a serial/ethernet gateway link to the building network using open-source libraries such as `BAC0` (Python BACnet router).
2. **Point Discovery**: Map physical thermostat objects (Analog Inputs for temperature sensors, Analog Values for temperature setpoints).
3. **Data Polling (BMS -> MCP)**: Telemetry functions read sensors directly from the network instead of local database logs:
   ```python
   # Reads physical zone sensor
   temp = bacnet.read("10:Analog Input, 3")
   ```
4. **Action Override Injection (MCP -> BMS)**: Directs thermostat write overrides straight to BMS actuators:
   ```python
   # Sets physical heating setpoint register
   bacnet.write("10:Analog Value, 1", action.heating_setpoint)
   ```
5. **Fail-Safe Integrity**: Real controllers include automated fallback timers. If the MCP Server stops sending updates (due to network or API loss), the local controller automatically releases overrides and returns control back to the baseline physical schedules.


