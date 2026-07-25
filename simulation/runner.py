import os
import sys
import pandas as pd

# Insert path to EnergyPlus API
EP_PATH = "/Applications/EnergyPlus-26-1-0"
if EP_PATH not in sys.path:
    sys.path.insert(0, EP_PATH)

from pyenergyplus.api import EnergyPlusAPI

class SimulationRunner:
    def __init__(self, idf_path, epw_path, output_dir):
        self.idf_path = idf_path
        self.epw_path = epw_path
        self.output_dir = output_dir
        self.api = EnergyPlusAPI()
        
        # Telemetry logs
        self.data_records = []
        
        # Actuators and Variable Handles
        self.handles_initialized = False
        self.outdoor_temp_handle = -1
        self.zone_temp_handles = {}
        self.cooling_setpoint_handle = -1
        self.heating_setpoint_handle = -1
        self.facility_power_handle = -1

    def initialize_handles(self, state):
        if self.handles_initialized:
            return
        
        # Request sensor handles
        self.outdoor_temp_handle = self.api.exchange.get_variable_handle(
            state, "Site Outdoor Air Drybulb Temperature", "Environment"
        )
        
        # 5 Zones in building: SPACE1-1, SPACE2-1, SPACE3-1, SPACE4-1, SPACE5-1
        zones = ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]
        for zone in zones:
            self.zone_temp_handles[zone] = self.api.exchange.get_variable_handle(
                state, "Zone Air Temperature", zone
            )
            
        self.cooling_setpoint_handle = self.api.exchange.get_actuator_handle(
            state, "Schedule:Compact", "Schedule Value", "CLG-SETP-SCH"
        )
        self.heating_setpoint_handle = self.api.exchange.get_actuator_handle(
            state, "Schedule:Compact", "Schedule Value", "HTG-SETP-SCH"
        )

        self.pmv_handle = self.api.exchange.get_variable_handle(
            state, "Zone Thermal Comfort Fanger Model PMV", "SPACE1-1 PEOPLE 1"
        )
        print(f"PMV Handle Query Result: {self.pmv_handle}")

        self.facility_power_handle = self.api.exchange.get_variable_handle(
            state, "Facility Total Purchased Electricity Energy", "Whole Building"
        )
        print(f"INITIALIZED - outdoor_temp_handle: {self.outdoor_temp_handle}")
        print(f"INITIALIZED - facility_power_handle: {self.facility_power_handle}")
        print(f"INITIALIZED - pmv_handle: {self.pmv_handle}")
        self.handles_initialized = True

    def callback_function(self, state):
        if self.api.exchange.warmup_flag(state):
            return
        if not self.api.exchange.api_data_fully_ready(state):
            return
            
        self.initialize_handles(state)
        
        # Read current timestep telemetry
        outdoor_temp = self.api.exchange.get_variable_value(state, self.outdoor_temp_handle)
        if self.facility_power_handle == -1:
            self.facility_power_handle = self.api.exchange.get_variable_handle(
                state, "Facility Total Purchased Electricity Energy", "Whole Building"
            )
        facility_power = self.api.exchange.get_variable_value(state, self.facility_power_handle) if self.facility_power_handle != -1 else 0.0
        if self.pmv_handle == -1:
            self.pmv_handle = self.api.exchange.get_variable_handle(
                state, "Zone Thermal Comfort Fanger Model PMV", "SPACE1-1 PEOPLE 1"
            )
        pmv_val = self.api.exchange.get_variable_value(state, self.pmv_handle) if self.pmv_handle != -1 else 0.0
        
        # Read temperatures for all zones
        zone_temps = {}
        for zone, handle in self.zone_temp_handles.items():
            if handle != -1:
                zone_temps[zone] = self.api.exchange.get_variable_value(state, handle)
                
        # Read current simulation time details
        day = self.api.exchange.day_of_month(state)
        month = self.api.exchange.month(state)
        hour = self.api.exchange.hour(state)
        minute = self.api.exchange.minutes(state)
        
        # Record data row
        record = {
            "Month": month,
            "Day": day,
            "Hour": hour,
            "Minute": minute,
            "OutdoorTemp": outdoor_temp,
            "FacilityPower": facility_power,
            "PMV": pmv_val,
            **{f"Temp_{z}": t for z, t in zone_temps.items()}
        }
        self.data_records.append(record)

    def run(self):
        print(f"Starting EnergyPlus simulation...")
        state = self.api.state_manager.new_state()
        
        # Register simulation callback at each timestep end
        self.api.runtime.callback_end_zone_timestep_after_zone_reporting(
            state, self.callback_function
        )
        
        # Prepare execution args
        args = [
            "-w", self.epw_path,
            "-d", self.output_dir,
            self.idf_path
        ]
        
        # Start execution
        self.api.runtime.run_energyplus(state, args)
        
        # Export keys list
        csv_bytes = self.api.exchange.list_available_api_data_csv(state)
        with open("simulation/test_run/api_data_keys.csv", "wb") as f:
            f.write(csv_bytes)
        print("Exported API data keys file!")

        self.api.state_manager.delete_state(state)
        print("Simulation Completed successfully!")
        
        # Save telemetry metrics
        df = pd.DataFrame(self.data_records)
        output_csv = os.path.join(self.output_dir, "telemetry.csv")
        df.to_csv(output_csv, index=False)
        print(f"Saved simulation metrics log to {output_csv}")
        return df

if __name__ == "__main__":
    runner = SimulationRunner(
        idf_path="simulation/building.idf",
        epw_path="simulation/weather.epw",
        output_dir="simulation/test_run"
    )
    runner.run()
