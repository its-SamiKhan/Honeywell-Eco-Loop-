import os
import json
import requests
import pandas as pd

class AgentLoop:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY must be provided or set in the environment.")
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def decide_setpoints(self, current_temp, outdoor_temp, pmv_index, electricity_kWh):
        """
        Queries Llama 3 8B via Groq to make optimization setpoint decisions.
        """
        system_prompt = (
            "You are an HVAC optimization controller AI. Your goal is to maximize energy savings "
            "while maintaining occupant thermal comfort. The Fanger PMV index must stay strictly between -0.7 and +0.7.\n"
            "Respond ONLY with a valid JSON block containing:\n"
            "{\n"
            "  \"heating_setpoint\": float,\n"
            "  \"cooling_setpoint\": float,\n"
            "  \"reasoning\": \"string\"\n"
            "}"
        )
        
        user_message = (
            f"Current Zone Temperature: {current_temp:.2f}°C\n"
            f"Outdoor Temperature: {outdoor_temp:.2f}°C\n"
            f"Fanger Comfort Index (PMV): {pmv_index:.3f}\n"
            f"Facility Timestep Electricity Used: {electricity_kWh:.2f} kWh\n\n"
            "Suggest new Heating & Cooling setpoints (valid cooling setpoint must be higher than heating setpoint)."
        )

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        try:
            res = requests.post(self.url, headers=self.headers, json=payload, timeout=8)
            res.raise_for_status()
            data = res.json()
            response_text = data["choices"][0]["message"]["content"]
            parsed = json.loads(response_text)
            return parsed["heating_setpoint"], parsed["cooling_setpoint"], parsed.get("reasoning", "")
        except Exception as e:
            print(f"[LLM Agent Error] Failed to get response from Groq API: {e}. Falling back to default rules.")
            # Fallback heating/cooling setpoints (Rule-based comfort backup)
            if pmv_index < -0.5:
                return 21.0, 24.0, "PMV too cold, warming up zone."
            elif pmv_index > 0.5:
                return 18.0, 22.0, "PMV too hot, cooling down zone."
            else:
                return 19.5, 23.5, "PMV comfortable, backing off setpoints to save energy."

if __name__ == "__main__":
    # Test stub
    agent = AgentLoop()
    h, c, r = agent.decide_setpoints(20.5, 2.0, -0.6, 2.5)
    print(f"Test Run Suggestion - Heating: {h}, Cooling: {c}, Reasoning: {r}")
