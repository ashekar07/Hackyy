"""
=============================================================================
COST & ESG AGENT - Financial ROI & Environmental Footprint Accountant
=============================================================================
Goal:
- Calculates money saved by preventing food overprep.
- Uses standard environmental formulas to calculate CO2 prevented and water conserved.
  * 1 kg food saved = 2.5 kg CO2 avoided
  * 1 kg food saved = 13.2 Liters of culinary water conserved

API Key:
- Reads the API key from the .env file via config.API_KEY to power AI reasoning.
=============================================================================
"""
import os
from typing import Dict, List, Any
from datetime import datetime

import config
from llm_client import LLMClient
from models.state import CostAndESGMetrics, AgentLogEntry

class CostAgent:
    """
    Computes financial savings and ESG environmental impact without hallucinations.
    """
    def __init__(self, api_key: str = None):
        self.name = "Cost & ESG Agent"
        self.role = "Deterministic Financial ROI & Carbon Accountant"
        # API key loaded from .env file
        self.api_key = api_key or config.API_KEY
        self.llm = LLMClient(api_key=self.api_key)

    def calculate(
        self,
        recipes: List[Dict[str, Any]],
        consensus_dict: Dict[str, int],
        inventory: List[Dict[str, Any]]
    ) -> CostAndESGMetrics:
        """
        Step 1: Calculate total baseline cost vs consensus recommended prep cost.
        Step 2: Calculate food saved in kg and direct ingredient dollars saved.
        Step 3: Calculate environmental offsets (CO2 prevented and water conserved).
        """
        total_baseline_cost = 0.0
        total_recommended_cost = 0.0
        total_food_saved_kg = 0.0
        total_avoided_loss_usd = 0.0

        for recipe in recipes:
            r_id = recipe["recipe_id"]
            base_portions = recipe["default_portions"]
            rec_portions = consensus_dict.get(r_id, base_portions)
            portion_g = recipe["portion_size_g"]
            unit_cost = recipe["unit_portion_cost"]

            # Financial commitments
            dish_baseline = base_portions * unit_cost
            dish_rec = rec_portions * unit_cost

            total_baseline_cost += dish_baseline
            total_recommended_cost += dish_rec

            # Food savings
            diff = base_portions - rec_portions
            if diff > 0:
                saved_kg = (diff * portion_g) / 1000.0
                total_food_saved_kg += saved_kg
                total_avoided_loss_usd += (diff * unit_cost)

        total_food_saved_kg = round(total_food_saved_kg, 1)

        # Environmental derivations
        co2_prevented = round(total_food_saved_kg * config.EMISSIONS_FACTOR_CO2_PER_KG, 1)
        water_conserved = round(total_food_saved_kg * config.WATER_CONSERVATION_L_PER_KG, 1)

        # ROI percentage
        roi_pct = 0.0
        if total_recommended_cost > 0:
            roi_pct = (total_avoided_loss_usd / total_recommended_cost) * 100.0

        return CostAndESGMetrics(
            baseline_prep_cost_usd=round(total_baseline_cost, 2),
            recommended_prep_cost_usd=round(total_recommended_cost, 2),
            avoided_loss_usd=round(total_avoided_loss_usd, 2),
            food_saved_kg=total_food_saved_kg,
            co2_prevented_kg=co2_prevented,
            water_conserved_liters=water_conserved,
            roi_percentage=round(roi_pct, 1)
        )

    def generate_log(self, metrics: CostAndESGMetrics, footfall_actual: int = 750) -> AgentLogEntry:
        """Generates the agent log entry with AI reasoning using the API key."""
        loss_func = "L_cost = Raw Food Expenditure Avoidance - Overprep Waste"
        inputs_summary = f"Avoided loss: ${metrics.avoided_loss_usd:.2f}, food saved: {metrics.food_saved_kg} kg"
        llm_res = self.llm.generate_agent_reasoning(
            self.name, self.role, loss_func, inputs_summary,
            {"footfall": footfall_actual, "details": metrics.model_dump()}
        )

        return AgentLogEntry(
            id=f"log_cost_{datetime.now().strftime('%H%M%S')}",
            timestamp=datetime.now().strftime("%H:%M:%S"),
            agent_name=self.name,
            agent_role=self.role,
            status="DECIDED",
            headline=f"Verified +${metrics.avoided_loss_usd:,.2f} avoided loss ({metrics.food_saved_kg} kg food diverted)",
            reasoning=(
                f"Applied deterministic formulas: {metrics.food_saved_kg} kg food saved * {config.EMISSIONS_FACTOR_CO2_PER_KG} = "
                f"{metrics.co2_prevented_kg} kg CO2e offset. Water preserved: {metrics.water_conserved_liters:,.0f} L."
            ),
            loss_function=loss_func,
            inputs_ingested=[
                f"Ingredient Unit Cost Database",
                f"Scope 3 GHG Factor: {config.EMISSIONS_FACTOR_CO2_PER_KG} kg CO2e / kg diverted",
                f"Culinary Water Factor: {config.WATER_CONSERVATION_L_PER_KG} L / kg saved",
                f"Direct Avoided Loss: ${metrics.avoided_loss_usd:,.2f}"
            ],
            detailed_analysis=llm_res["reasoning"],
            llm_source=f"{llm_res['source']} ({llm_res['model']})",
            metrics={
                "avoided_loss_usd": f"${metrics.avoided_loss_usd:,.2f}",
                "food_saved_kg": f"{metrics.food_saved_kg} kg",
                "co2_prevented_kg": f"{metrics.co2_prevented_kg} kg",
                "water_liters": f"{metrics.water_conserved_liters:,.0f} L"
            },
            confidence=0.99
        )
