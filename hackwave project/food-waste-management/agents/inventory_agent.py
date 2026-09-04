"""
=============================================================================
INVENTORY AGENT - Perishability Defender & Shelf-Life Tracker
=============================================================================
Goal:
- Scans inventory items to find ingredients expiring in under 24 hours.
- Insists on cooking dishes that use up expiring items to prevent spoilage.

API Key:
- Reads the API key from the .env file via config.API_KEY to power AI reasoning.
=============================================================================
"""
import os
from typing import Dict, List, Any
from datetime import datetime

import config
from llm_client import LLMClient
from models.state import AgentLogEntry, ArbitrationArgument

class InventoryAgent:
    """
    Prevents raw ingredient spoilage by monitoring shelf life hours.
    """
    def __init__(self, api_key: str = None):
        self.name = "Inventory Agent"
        self.role = "Perishability Defender & Shelf-Life Tracker"
        # API key loaded from .env file
        self.api_key = api_key or config.API_KEY
        self.llm = LLMClient(api_key=self.api_key)

    def analyze(
        self,
        recipes: List[Dict[str, Any]],
        inventory: List[Dict[str, Any]],
        footfall_actual: int
    ) -> Dict[str, Any]:
        """
        Step 1: Identify all ingredients expiring in < 24 hours.
        Step 2: Propose portion floor for recipes using expiring stock.
        Step 3: Generate AI reasoning using the API key from .env.
        """
        # Find ingredients expiring soon
        expiring_ingredients: Dict[str, Dict[str, Any]] = {}
        for item in inventory:
            hours_left = item.get("shelf_life_hours_remaining", 999.0)
            if hours_left <= config.EXPIRY_URGENCY_HOURS:
                expiring_ingredients[item["ingredient_id"]] = item

        arguments: Dict[str, ArbitrationArgument] = {}
        proposed_portions: Dict[str, int] = {}
        critical_alerts: List[str] = []

        for recipe in recipes:
            r_id = recipe["recipe_id"]
            dish_name = recipe["dish_name"]
            req_ingredients = recipe.get("ingredients_per_portion", {})
            
            # Check if this recipe consumes any expiring ingredient
            tied_expiring_items: List[str] = []
            max_recommended = recipe["default_portions"]

            for ing_id, qty_per_portion in req_ingredients.items():
                if ing_id in expiring_ingredients:
                    exp_item = expiring_ingredients[ing_id]
                    kg_on_hand = exp_item["kg_on_hand"]
                    hours = exp_item["shelf_life_hours_remaining"]
                    tied_expiring_items.append(f"{exp_item['name']} ({hours:.1f}h left)")
                    
                    # Target exhausting at least 70% of the expiring lot
                    portions_to_exhaust = int(round((kg_on_hand * 0.70) / max(0.01, qty_per_portion)))
                    max_recommended = max(max_recommended, portions_to_exhaust)

            if tied_expiring_items:
                # Inventory agent demands elevated portions to save the raw ingredient
                forced_portions = min(max_recommended, int(recipe["default_portions"] * 1.25))
                priority = "CRITICAL"
                critical_alerts.append(f"{dish_name}: uses {', '.join(tied_expiring_items)}")
                rationale = (
                    f"URGENT SHELF-LIFE RISK: Consumes {', '.join(tied_expiring_items)}. "
                    f"Demanding floor batch of {forced_portions} portions to prevent dumping raw ingredients tonight."
                )
            else:
                # Non-perishable or stable: scaled cleanly with diner footfall
                footfall_factor = footfall_actual / max(1, config.BASELINE_CAMPUS_FOOTFALL)
                forced_portions = int(round(recipe["default_portions"] * footfall_factor))
                priority = "NORMAL"
                rationale = "Storage stock stable (>24h shelf life). No immediate spoilage hazard."

            proposed_portions[r_id] = forced_portions
            arguments[r_id] = ArbitrationArgument(
                agent_name=self.name,
                proposed_portions=forced_portions,
                safety_margin_pct=15.0 if tied_expiring_items else 0.0,
                rationale=rationale,
                priority_level=priority
            )

        # Generate intelligent reasoning using API key
        loss_func = "L_inventory = Raw Ingredient Spoilage Cost (FIFO <24h)"
        inputs_summary = f"{len(expiring_ingredients)} perishable lots expiring in <{int(config.EXPIRY_URGENCY_HOURS)}h"
        llm_res = self.llm.generate_agent_reasoning(
            self.name, self.role, loss_func, inputs_summary,
            {"footfall": footfall_actual, "details": proposed_portions}
        )

        log = AgentLogEntry(
            id=f"log_inv_{footfall_actual}",
            timestamp=datetime.now().strftime("%H:%M:%S"),
            agent_name=self.name,
            agent_role=self.role,
            status="ALERT" if critical_alerts else "DECIDED",
            headline=(
                f"Identified {len(expiring_ingredients)} perishable lots expiring in < {int(config.EXPIRY_URGENCY_HOURS)}h"
                if expiring_ingredients else "All cold-storage lots within safe shelf-life"
            ),
            reasoning=(
                f"Scanned cold storage shelf life. Critical stock: "
                f"{', '.join([f'{i['name']} ({i['shelf_life_hours_remaining']}h)' for i in expiring_ingredients.values()]) if expiring_ingredients else 'None'}."
            ),
            loss_function=loss_func,
            inputs_ingested=[
                f"Total Inventory Items Monitored: {len(inventory)}",
                f"Perishable Items Expiring Soon: {len(expiring_ingredients)}",
                f"Urgent Threshold: {int(config.EXPIRY_URGENCY_HOURS)} Hours"
            ],
            detailed_analysis=llm_res["reasoning"],
            llm_source=f"{llm_res['source']} ({llm_res['model']})",
            metrics={
                "expiring_lots_count": len(expiring_ingredients),
                "threshold_hours": config.EXPIRY_URGENCY_HOURS,
                "urgently_targeted_dishes": len(critical_alerts)
            },
            confidence=0.96
        )

        return {
            "proposed_portions": proposed_portions,
            "arguments": arguments,
            "log": log
        }
