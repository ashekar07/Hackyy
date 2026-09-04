"""
=============================================================================
FOOD WASTE MANAGEMENT - SIMULATION PIPELINE & STATE COORDINATOR
=============================================================================
This pipeline coordinates the entire system in 4 clear, simple steps:
1. Ingests and converts user data files via data_loader.py.
2. Runs the Worker Agents (Demand, Waste, Inventory) with API keys from .env.
3. Runs the Orchestrator Agent to resolve trade-offs and lock consensus portions.
4. Calculates financial/ESG savings (Cost Agent) and 2-shift prep schedules (Action Agent).
=============================================================================
"""
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.state import (
    KitchenState,
    SimulationScenario,
    RecipePrepOrder,
    AgentLogEntry,
    CounterFactualImpact
)
from agents.demand_agent import DemandAgent
from agents.waste_agent import WasteAgent
from agents.inventory_agent import InventoryAgent
from agents.orchestrator import OrchestratorAgent
from agents.cost_agent import CostAgent
from agents.action_agent import ActionAgent
import config
from data_loader import load_all_data

# Preset simulation scenarios for demonstrations and testing
PRESET_SCENARIOS = {
    "NORMAL": SimulationScenario(
        scenario_id="NORMAL",
        title="Standard Lunch Service",
        description="Clear skies (24°C), standard campus attendance. Regular dining hall timetable.",
        footfall=750,
        weather_factor=1.0,
        exam_factor=1.0,
        chiller_status="NOMINAL (3.2°C)"
    ),
    "MONSOON": SimulationScenario(
        scenario_id="MONSOON",
        title="Torrential Monsoon Downpour (-44% Pax)",
        description="Heavy storm outside. Commuter diners unable to reach dining hall; footfall drops sharply.",
        footfall=420,
        weather_factor=0.68,
        exam_factor=1.0,
        chiller_status="NOMINAL (3.4°C)"
    ),
    "EXAM_SURGE": SimulationScenario(
        scenario_id="EXAM_SURGE",
        title="Finals Week Quick-Lunch Rush (+27% Pax)",
        description="Exam revision week. High-density dining hall rush with rapid table turnover.",
        footfall=950,
        weather_factor=1.0,
        exam_factor=1.18,
        chiller_status="NOMINAL (3.0°C)"
    ),
    "CHILLER_FAIL": SimulationScenario(
        scenario_id="CHILLER_FAIL",
        title="Chiller #1 Thermal Alarm (Spoilage Hazard)",
        description="Chiller temperature warning. Perishable dairy and cream shelf life reduced to < 8 hours!",
        footfall=680,
        weather_factor=0.95,
        exam_factor=1.0,
        chiller_status="WARNING (8.6°C - Thermal Drift)"
    )
}

class KitchenSynapseEngine:
    """
    Coordinates data ingestion, multi-agent arbitration, and live state management.
    """
    def __init__(self, data_dir: str):
        self.data_dir = data_dir

        # Initialize all 6 specialized agents (each uses the API key from .env)
        self.demand_agent = DemandAgent()
        self.waste_agent = WasteAgent()
        self.inventory_agent = InventoryAgent()
        self.orchestrator = OrchestratorAgent()
        self.cost_agent = CostAgent()
        self.action_agent = ActionAgent()

        self.active_overrides: Dict[str, int] = {}
        self.current_state: Optional[KitchenState] = None

        # Load user data from files and initialize simulation
        self.load_data()
        self.run_cycle(PRESET_SCENARIOS["NORMAL"])

    def load_data(self):
        """
        Takes files stored by user in data_dir and converts them for the agents.
        """
        loaded = load_all_data(self.data_dir)
        self.recipes = loaded["recipes"]
        self.inventory = loaded["inventory"]
        self.waste_logs = loaded["waste_logs"]

    def run_cycle(
        self,
        scenario: SimulationScenario,
        custom_footfall: Optional[int] = None,
        overrides: Optional[Dict[str, int]] = None
    ) -> KitchenState:
        """
        Executes the 4-step multi-agent cycle:
        """
        if overrides is not None:
            self.active_overrides = overrides

        footfall = custom_footfall if custom_footfall is not None else scenario.footfall

        # Simulate perishable urgency if chiller thermal alarm is triggered
        active_inventory = [dict(item) for item in self.inventory]
        if scenario.scenario_id == "CHILLER_FAIL":
            for item in active_inventory:
                if "ing_paneer" in item.get("ingredient_id", "") or "ing_cream" in item.get("ingredient_id", ""):
                    item["shelf_life_hours_remaining"] = 6.0

        # -------------------------------------------------------------------
        # STEP 1: Worker Agents Analyze (Using API Key for Reasoning)
        # -------------------------------------------------------------------
        demand_res = self.demand_agent.analyze(
            self.recipes, footfall, scenario.weather_factor, scenario.exam_factor
        )
        waste_res = self.waste_agent.analyze(
            self.recipes, self.waste_logs, footfall, scenario.weather_factor
        )
        inventory_res = self.inventory_agent.analyze(
            self.recipes, active_inventory, footfall
        )

        # -------------------------------------------------------------------
        # STEP 2: Orchestrator Mediates Conflicts & Finds Consensus
        # -------------------------------------------------------------------
        arb_rounds, consensus_dict, orch_log = self.orchestrator.run_arbitration(
            self.recipes, demand_res, waste_res, inventory_res
        )

        # -------------------------------------------------------------------
        # STEP 3: Cost & ESG Agent Calculates Financial and Carbon Savings
        # -------------------------------------------------------------------
        cost_metrics = self.cost_agent.calculate(
            self.recipes, consensus_dict, active_inventory
        )
        cost_log = self.cost_agent.generate_log(cost_metrics, footfall_actual=footfall)

        # -------------------------------------------------------------------
        # STEP 4: Action Agent Schedules Staged Cooking & Surplus Routing
        # -------------------------------------------------------------------
        batch_orders = self.action_agent.build_prep_orders(
            self.recipes,
            self.waste_logs,
            active_inventory,
            consensus_dict,
            self.active_overrides
        )
        surplus_items = self.action_agent.plan_surplus_dispatch(
            batch_orders, footfall, config.BASELINE_CAMPUS_FOOTFALL
        )
        action_log = self.action_agent.generate_log(
            batch_orders, len(surplus_items), footfall_actual=footfall
        )

        # Evaluate chef manual overrides if present
        counter_factual: Optional[CounterFactualImpact] = None
        for r_id, override_val in self.active_overrides.items():
            if r_id in batch_orders:
                counter_factual = self.action_agent.evaluate_chef_override(
                    r_id, override_val, batch_orders[r_id]
                )
                break

        # Assemble unified state
        from llm_client import llm_client
        agent_logs = [
            demand_res["log"],
            waste_res["log"],
            inventory_res["log"],
            orch_log,
            cost_log,
            action_log
        ]

        self.current_state = KitchenState(
            scenario=scenario,
            footfall_actual=footfall,
            footfall_baseline=config.BASELINE_CAMPUS_FOOTFALL,
            agent_logs=agent_logs,
            arbitration_log=arb_rounds,
            batch_orders=batch_orders,
            cost_esg=cost_metrics,
            surplus_dispatch=surplus_items,
            counter_factual=counter_factual,
            featherless_info={
                "configured": llm_client.is_configured(),
                "masked_key": llm_client.get_masked_key(),
                "model": llm_client.model,
                "base_url": llm_client.base_url
            },
            dataset_info={
                "recipes_count": len(self.recipes),
                "inventory_count": len(self.inventory),
                "waste_logs_count": len(self.waste_logs.get("historical_metrics", {})),
                "recipes": self.recipes,
                "inventory": self.inventory,
                "waste_logs": self.waste_logs
            }
        )
        return self.current_state

    def apply_chef_override(self, dish_id: str, portions: int) -> KitchenState:
        """Applies a chef manual override for a specific recipe."""
        self.active_overrides[dish_id] = portions
        if self.current_state:
            return self.run_cycle(
                self.current_state.scenario,
                custom_footfall=self.current_state.footfall_actual,
                overrides=self.active_overrides
            )
        return self.run_cycle(PRESET_SCENARIOS["NORMAL"], overrides=self.active_overrides)

    def reset_overrides(self) -> KitchenState:
        """Clears all manual overrides and reverts to AI consensus."""
        self.active_overrides.clear()
        if self.current_state:
            return self.run_cycle(
                self.current_state.scenario,
                custom_footfall=self.current_state.footfall_actual,
                overrides={}
            )
        return self.run_cycle(PRESET_SCENARIOS["NORMAL"], overrides={})

# Alias for clean modern naming
FoodWasteEngine = KitchenSynapseEngine
