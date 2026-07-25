import os
import sys
import pandas as pd
import json

# Setup environment paths
EP_PATH = "/Applications/EnergyPlus-26-1-0"
if EP_PATH not in sys.path:
    sys.path.insert(0, EP_PATH)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyenergyplus.api import EnergyPlusAPI
from agent.agent_loop import AgentLoop

class ClosedLoopSimulation:
    def __init__(self, idf_path, epw_path, output_dir, api_key=None):
        self.idf_path = idf_path
        self.epw_path = epw_path
        self.output_dir = output_dir
        self.api = EnergyPlusAPI()
        self.agent = AgentLoop(api_key=api_key)
        
        # Telemetry logs
        self.data_records = []
        
        # Actuators and Variable Handles
        self.handles_initialized = False
        self.outdoor_temp_handle = -1
        self.zone_temp_handles = {}
        self.cooling_setpoint_handle = -1
        self.heating_setpoint_handle = -1
        self.facility_power_handle = -1
        self.pmv_handle = -1
        
        # Decision Interval Control (Only query LLM every 4 timesteps/1 hour to save API calls)
        self.decision_counter = 0

    def initialize_handles(self, state):
        if self.handles_initialized:
            return
        
        # Request sensor handles
        self.outdoor_temp_handle = self.api.exchange.get_variable_handle(
            state, "Site Outdoor Air Drybulb Temperature", "Environment"
        )
        
        zones = ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]
        for zone in zones:
            self.zone_temp_handles[zone] = self.api.exchange.get_variable_handle(
                state, "Zone Air Temperature", zone
            )
            
        # Expose Actuators to dynamically alter global Heating/Cooling thermostat setpoint schedules
        self.cooling_setpoint_handle = self.api.exchange.get_actuator_handle(
            state, "Schedule:Compact", "Schedule Value", "CLG-SETP-SCH"
        )
        self.heating_setpoint_handle = self.api.exchange.get_actuator_handle(
            state, "Schedule:Compact", "Schedule Value", "HTG-SETP-SCH"
        )
        
        self.pmv_handle = self.api.exchange.get_variable_handle(
            state, "Zone Thermal Comfort Fanger Model PMV", "SPACE1-1 PEOPLE 1"
        )
        
        self.facility_power_handle = self.api.exchange.get_variable_handle(
            state, "Facility Total Purchased Electricity Energy", "Whole Building"
        )
        
        self.handles_initialized = True

    def callback_function(self, state):
        # Skip warmups
        if self.api.exchange.warmup_flag(state):
            return
        if not self.api.exchange.api_data_fully_ready(state):
            return
            
        self.initialize_handles(state)
        
        # Read current timestep values
        outdoor_temp = self.api.exchange.get_variable_value(state, self.outdoor_temp_handle)
        facility_power = self.api.exchange.get_variable_value(state, self.facility_power_handle)
        pmv_val = self.api.exchange.get_variable_value(state, self.pmv_handle) if self.pmv_handle != -1 else 0.0
        
        # Read temperatures for all zones (we'll focus SPACE1-1 for LLM optimization control)
        zone_temps = {}
        for zone, handle in self.zone_temp_handles.items():
            if handle != -1:
                zone_temps[zone] = self.api.exchange.get_variable_value(state, handle)
        
        current_temp = zone_temps.get("SPACE1-1", 20.0)
        
        # Run Closed-Loop decision logic at every 4 timesteps (1-hour decisions)
        self.decision_counter += 1
        
        # Convert J to kWh
        electricity_kWh = (facility_power / 3600000.0) if facility_power > 0 else 0.0
        
        heating_setpoint = 19.5
        cooling_setpoint = 23.5
        reasoning = "Using default fallback setpoints"
        
        if self.decision_counter % 4 == 0:
            # Query LLM Agent for optimal setpoints
            heating_setpoint, cooling_setpoint, reasoning = self.agent.decide_setpoints(
                current_temp=current_temp,
                outdoor_temp=outdoor_temp,
                pmv_index=pmv_val,
                electricity_kWh=electricity_kWh
            )
            print(f"[AI Control Timestep] Sugessted Heating: {heating_setpoint}°C, Cooling: {cooling_setpoint}°C | Reason: {reasoning}")
            
            # Apply LLM recommendations to the active simulator actuators
            if self.cooling_setpoint_handle != -1:
                self.api.exchange.set_actuator_value(state, self.cooling_setpoint_handle, cooling_setpoint)
            if self.heating_setpoint_handle != -1:
                self.api.exchange.set_actuator_value(state, self.heating_setpoint_handle, heating_setpoint)
                
        # Record stats row
        day = self.api.exchange.day_of_month(state)
        month = self.api.exchange.month(state)
        hour = self.api.exchange.hour(state)
        minute = self.api.exchange.minutes(state)
        
        record = {
            "Month": month,
            "Day": day,
            "Hour": hour,
            "Minute": minute,
            "OutdoorTemp": outdoor_temp,
            "FacilityPower": facility_power,
            "PMV": pmv_val,
            "HeatingSetpoint": heating_setpoint,
            "CoolingSetpoint": cooling_setpoint,
            "AgentReasoning": reasoning,
            **{f"Temp_{z}": t for z, t in zone_temps.items()}
        }
        self.data_records.append(record)

    def run(self):
        print("Initializing Closed Loop AI simulation...")
        state = self.api.state_manager.new_state()
        
        # Register simulation callback at each timestep end
        self.api.runtime.callback_end_zone_timestep_after_zone_reporting(
            state, self.callback_function
        )
        
        args = [
            "-w", self.epw_path,
            "-d", self.output_dir,
            self.idf_path
        ]
        
        self.api.runtime.run_energyplus(state, args)
        self.api.state_manager.delete_state(state)
        print("Closed-loop simulation complete!")
        
        # Save telemetry metrics
        df = pd.DataFrame(self.data_records)
        output_csv = os.path.join(self.output_dir, "ai_telemetry.csv")
        df.to_csv(output_csv, index=False)
        print(f"Saved AI control metrics log to {output_csv}")
        return df

if __name__ == "__main__":
    runner = ClosedLoopSimulation(
        idf_path="simulation/building.idf",
        epw_path="simulation/weather.epw",
        output_dir="simulation/test_run"
    )
    runner.run()
