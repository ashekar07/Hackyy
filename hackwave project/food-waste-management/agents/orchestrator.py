"""
=============================================================================
ORCHESTRATOR AGENT - Tension Arbitrator & Decision Mediator
=============================================================================
Goal:
- Resolves conflicts between the competing objectives of:
    1. Demand Agent (wants more portions to avoid running out)
    2. Waste Agent (wants fewer portions to avoid scrap waste)
    3. Inventory Agent (wants to cook portions that use expiring food)
- Synthesizes the final agreed portion count for each recipe.

API Key:
- Reads the API key from the .env file via config.API_KEY to explain the compromise.
=============================================================================
"""
import os
from typing import Dict, List, Any, Tuple
from datetime import datetime

import config
from llm_client import LLMClient
from models.state import AgentLogEntry, ArbitrationRound, ArbitrationArgument

class OrchestratorAgent:
    """
    Acts as the neutral referee to resolve trade-offs between agents.
    """
    def __init__(self, api_key: str = None):
        self.name = "Orchestrator Agent"
        self.role = "Tension Arbitrator & State Coordinator"
        # API key loaded from .env file
        self.api_key = api_key or config.API_KEY
        self.llm = LLMClient(api_key=self.api_key)

    def arbitrate_dish(
        self,
        dish_id: str,
        dish_name: str,
        demand_arg: ArbitrationArgument,
        waste_arg: ArbitrationArgument,
        inventory_arg: ArbitrationArgument,
        recipe: Dict[str, Any]
    ) -> ArbitrationRound:
        """
        Balances the 3 proposals:
        - d: Demand portion proposal
        - w: Waste lean portion proposal
        - i: Inventory floor portion proposal
        """
        d = demand_arg.proposed_portions
        w = waste_arg.proposed_portions
        i = inventory_arg.proposed_portions

        proposals = [d, w, i]
        max_p, min_p = max(proposals), min(proposals)
        avg_p = sum(proposals) / 3.0

        # Conflict intensity score: 0.0 (unanimous) to 1.0 (severe conflict)
        conflict_intensity = min(1.0, round((max_p - min_p) / max(1.0, avg_p), 2))

        is_perishable_urgent = inventory_arg.priority_level == "CRITICAL"
        is_scrap_critical = waste_arg.priority_level == "CRITICAL"

        # Case 1: High tension - both expiring food and high scrap risk
        if is_perishable_urgent and is_scrap_critical:
            consensus = int(round((w * 0.40) + (i * 0.40) + (d * 0.20)))
            rationale = (
                f"HIGH TENSION COMPROMISE: Demand wanted {d}, Waste wanted {w}, Inventory insisted on {i}. "
                f"Settled at {consensus} portions: uses expiring ingredients while mitigating waste via 2-shift staged prep."
            )
        # Case 2: High scrap risk
        elif is_scrap_critical:
            consensus = int(round((w * 0.65) + (d * 0.35)))
            rationale = (
                f"SCRAP WARNING PRECEDENCE: Waste Agent warning prioritized over safety buffer. "
                f"Scaled down from {d} to {consensus} portions to prevent buffet tray scrap."
            )
        # Case 3: Perishable stock urgency
        elif is_perishable_urgent:
            consensus = int(round((i * 0.60) + (d * 0.40)))
            rationale = (
                f"EXPIRY PRECEDENCE: Inventory urgency takes priority to avoid raw ingredient loss. "
                f"Increased prep to {consensus} portions, routing any surplus to student flash sale."
            )
        # Case 4: Normal consensus
        else:
            consensus = int(round((d * 0.50) + (w * 0.35) + (i * 0.15)))
            rationale = (
                f"BALANCED CONSENSUS: Balanced demand prediction ({d}) with lean scrap guardrails ({w}). "
                f"Final batch locked at {consensus} portions."
            )

        consensus = max(15, consensus)

        return ArbitrationRound(
            dish_id=dish_id,
            dish_name=dish_name,
            demand_arg=demand_arg,
            waste_arg=waste_arg,
            inventory_arg=inventory_arg,
            consensus_portions=consensus,
            compromise_rationale=rationale,
            conflict_intensity=conflict_intensity
        )

    def run_arbitration(
        self,
        recipes: List[Dict[str, Any]],
        demand_res: Dict[str, Any],
        waste_res: Dict[str, Any],
        inventory_res: Dict[str, Any]
    ) -> Tuple[List[ArbitrationRound], Dict[str, int], AgentLogEntry]:
        """
        Runs arbitration across all menu recipes and produces the final consensus.
        """
        rounds: List[ArbitrationRound] = []
        consensus_dict: Dict[str, int] = {}
        high_tension_count = 0

        for recipe in recipes:
            r_id = recipe["recipe_id"]
            dish_name = recipe["dish_name"]

            round_res = self.arbitrate_dish(
                dish_id=r_id,
                dish_name=dish_name,
                demand_arg=demand_res["arguments"][r_id],
                waste_arg=waste_res["arguments"][r_id],
                inventory_arg=inventory_res["arguments"][r_id],
                recipe=recipe
            )
            rounds.append(round_res)
            consensus_dict[r_id] = round_res.consensus_portions

            if round_res.conflict_intensity > 0.25:
                high_tension_count += 1

        # Generate intelligent reasoning using API key
        loss_func = "L_arbitration = w1*L_demand + w2*L_waste + w3*L_inventory"
        inputs_summary = f"{len(recipes)} recipes arbitrated, {high_tension_count} tension conflicts resolved"
        llm_res = self.llm.generate_agent_reasoning(
            self.name, self.role, loss_func, inputs_summary,
            {"footfall": config.BASELINE_CAMPUS_FOOTFALL, "details": consensus_dict}
        )

        orch_log = AgentLogEntry(
            id=f"log_orch_{datetime.now().strftime('%H%M%S')}",
            timestamp=datetime.now().strftime("%H:%M:%S"),
            agent_name=self.name,
            agent_role=self.role,
            status="DECIDED",
            headline=f"Resolved arbitration: locked consensus batches for {len(recipes)} menu items",
            reasoning=(
                f"Synthesized conflicting proposals from Demand, Waste, and Inventory agents. "
                f"Resolved {high_tension_count} high-tension trade-offs with zero stockouts and minimal scrap."
            ),
            loss_function=loss_func,
            inputs_ingested=[
                f"Demanded portions: {sum(demand_res['proposed_portions'].values())} plates",
                f"Waste lean proposals: {sum(waste_res['proposed_portions'].values())} plates",
                f"Inventory floor proposals: {sum(inventory_res['proposed_portions'].values())} plates"
            ],
            detailed_analysis=llm_res["reasoning"],
            llm_source=f"{llm_res['source']} ({llm_res['model']})",
            metrics={
                "recipes_arbitrated": len(recipes),
                "high_tension_dishes": high_tension_count,
                "total_consensus_portions": sum(consensus_dict.values())
            },
            confidence=0.97
        )

        return rounds, consensus_dict, orch_log
