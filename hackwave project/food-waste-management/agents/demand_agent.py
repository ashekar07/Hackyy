"""
=============================================================================
DEMAND AGENT - Service Maximizer & Headcount Predictor
=============================================================================
Goal:
- Predicts diner demand for each recipe based on footfall and weather.
- Adds an 8% safety buffer so the kitchen never runs out of food mid-service.

API Key:
- Reads the API key from the .env file via config.API_KEY to power AI reasoning.
=============================================================================
"""
import os
import math
from typing import Dict, List, Any
from datetime import datetime

import config
from llm_client import LLMClient
from models.state import AgentLogEntry, ArbitrationArgument

class DemandAgent:
    """
    Predicts portions required to satisfy hungry diners without stockouts.
    """
    def __init__(self, api_key: str = None):
        self.name = "Demand Agent"
        self.role = "Service Maximizer & Headcount Predictor"
        # API key loaded from .env file
        self.api_key = api_key or config.API_KEY
        self.llm = LLMClient(api_key=self.api_key)

    def analyze(
        self,
        recipes: List[Dict[str, Any]],
        footfall_actual: int,
        weather_factor: float = 1.0,
        exam_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Step 1: Calculate demand multiplier based on diner footfall and weather.
        Step 2: Propose portion count for each recipe with a +8% safety buffer.
        Step 3: Generate AI reasoning using the API key from .env.
        """
        # Ratio of today's expected diners compared to baseline capacity (750 diners)
        footfall_ratio = footfall_actual / max(1, config.BASELINE_CAMPUS_FOOTFALL)
        multiplier = footfall_ratio * weather_factor * exam_factor
        
        proposed_portions: Dict[str, int] = {}
        arguments: Dict[str, ArbitrationArgument] = {}

        # Calculate portions for each recipe
        for recipe in recipes:
            r_id = recipe["recipe_id"]
            base_portions = recipe["default_portions"]
            
            # Staple dishes (like Rice & Dal) are more resistant to weather drops
            is_staple = "Staple" in recipe.get("category", "")
            elasticity = 0.85 if is_staple else 1.15
            adjusted_factor = math.pow(multiplier, elasticity)
            
            # Add safety buffer (+8%) so food never runs out
            buffer_multiplier = 1.0 + config.DEMAND_SAFETY_BUFFER
            portions = int(round(base_portions * adjusted_factor * buffer_multiplier))
            portions = max(20, portions)  # Minimum safety floor
            
            proposed_portions[r_id] = portions
            arguments[r_id] = ArbitrationArgument(
                agent_name=self.name,
                proposed_portions=portions,
                safety_margin_pct=round(config.DEMAND_SAFETY_BUFFER * 100, 1),
                rationale=(
                    f"Protecting guest fulfillment with a +{int(config.DEMAND_SAFETY_BUFFER*100)}% safety buffer. "
                    f"Factored {footfall_actual} diners and weather multiplier {weather_factor:.2f}."
                ),
                priority_level="HIGH" if portions > base_portions else "NORMAL"
            )

        # Generate intelligent reasoning using API key
        loss_func = "L_demand = Service Stockout Penalty (Buffer +8%)"
        inputs_summary = f"{footfall_actual} diners, weather {weather_factor:.2f}, safety buffer +8%"
        llm_res = self.llm.generate_agent_reasoning(
            self.name, self.role, loss_func, inputs_summary,
            {"footfall": footfall_actual, "details": proposed_portions}
        )

        log = AgentLogEntry(
            id=f"log_demand_{footfall_actual}",
            timestamp=datetime.now().strftime("%H:%M:%S"),
            agent_name=self.name,
            agent_role=self.role,
            status="DECIDED",
            headline=f"Demanded service buffer for {footfall_actual} expected diners",
            reasoning=(
                f"Computed headcount demand across recipes. Applying a {int(config.DEMAND_SAFETY_BUFFER*100)}% "
                f"protective ceiling against mid-service stockouts (weather factor {weather_factor:.2f})."
            ),
            loss_function=loss_func,
            inputs_ingested=[
                f"Turnstiles / Headcount ({footfall_actual} actual diners)",
                f"Weather Multiplier: {weather_factor:.2f}",
                f"Exam Multiplier: {exam_factor:.2f}",
                f"Demand Safety Buffer: +{int(config.DEMAND_SAFETY_BUFFER*100)}%"
            ],
            detailed_analysis=llm_res["reasoning"],
            llm_source=f"{llm_res['source']} ({llm_res['model']})",
            metrics={
                "projected_footfall": footfall_actual,
                "safety_buffer_pct": int(config.DEMAND_SAFETY_BUFFER * 100),
                "weather_multiplier": weather_factor
            },
            confidence=0.93
        )

        return {
            "proposed_portions": proposed_portions,
            "arguments": arguments,
            "log": log
        }
