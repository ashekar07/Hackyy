"""
=============================================================================
ACTION AGENT - Prep Scheduler & Surplus Logistics Planner
=============================================================================
Goal:
- Translates arbitrated portion counts into actionable culinary kitchen shifts:
    * Shift 1: 65% base cooked at 11:00 AM.
    * Shift 2: 35% on-demand held chilled until 1:15 PM confirmation.
- Plans surplus routing (Student Flash Sale or NGO Food Rescue).
- Calculates risk and mitigation if a chef manually overrides AI recommendations.

API Key:
- Reads the API key from the .env file via config.API_KEY to power AI reasoning.
=============================================================================
"""
import os
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

import config
from llm_client import LLMClient
from models.state import (
    RecipePrepOrder,
    BatchPrepShift,
    SurplusDispatchItem,
    CounterFactualImpact,
    AgentLogEntry
)

class ActionAgent:
    """
    Creates production schedules and surplus routing directives.
    """
    def __init__(self, api_key: str = None):
        self.name = "Action Agent"
        self.role = "Operational Prep Scheduler & Surplus Dispatcher"
        # API key loaded from .env file
        self.api_key = api_key or config.API_KEY
        self.llm = LLMClient(api_key=self.api_key)

    def build_prep_orders(
        self,
        recipes: List[Dict[str, Any]],
        waste_logs: Dict[str, Any],
        inventory: List[Dict[str, Any]],
        consensus_dict: Dict[str, int],
        overrides: Optional[Dict[str, int]] = None
    ) -> Dict[str, RecipePrepOrder]:
        """
        Creates cooking orders split into 2-shift staged batches.
        """
        overrides = overrides or {}
        historical = waste_logs.get("historical_metrics", {})
        orders: Dict[str, RecipePrepOrder] = {}

        for recipe in recipes:
            r_id = recipe["recipe_id"]
            dish_name = recipe["dish_name"]
            base_portions = recipe["default_portions"]
            rec_portions = consensus_dict.get(r_id, base_portions)
            override_val = overrides.get(r_id)

            active_portions = override_val if override_val is not None else rec_portions
            portion_g = recipe["portion_size_g"]
            total_kg = round((active_portions * portion_g) / 1000.0, 1)

            dish_stats = historical.get(r_id, {})
            scrap_pct = dish_stats.get("avg_scrap_rate_pct", 8.0)

            if scrap_pct >= 18.0:
                risk_level = "CRITICAL"
            elif scrap_pct >= 12.0:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            # Check expiring ingredients used
            exp_used = []
            for item in inventory:
                if item.get("shelf_life_hours_remaining", 999) < config.EXPIRY_URGENCY_HOURS:
                    if item["ingredient_id"] in recipe.get("ingredients_per_portion", {}):
                        exp_used.append(item["name"])

            # Staged 2-Shift Schedule (65% Base, 35% On-Demand)
            s1_count = int(round(active_portions * config.SHIFT_1_RATIO))
            s2_count = active_portions - s1_count

            s1_kg = round((s1_count * portion_g) / 1000.0, 1)
            s2_kg = round((s2_count * portion_g) / 1000.0, 1)

            shifts = [
                BatchPrepShift(
                    shift_id=f"{r_id}_s1",
                    shift_name=f"Shift 1: 11:00 AM ({int(config.SHIFT_1_RATIO*100)}% Base)",
                    portion_count=s1_count,
                    prep_kg=s1_kg,
                    action_directive="COOK_NOW",
                    time_window="11:00 AM - 12:30 PM"
                ),
                BatchPrepShift(
                    shift_id=f"{r_id}_s2",
                    shift_name=f"Shift 2: 1:15 PM ({int(config.SHIFT_2_RATIO*100)}% On-Demand)",
                    portion_count=s2_count,
                    prep_kg=s2_kg,
                    action_directive="HOLD_RAW_CHILLED",
                    time_window="1:15 PM - 2:30 PM (Trigger only if footfall > 80%)"
                )
            ]

            orders[r_id] = RecipePrepOrder(
                recipe_id=r_id,
                dish_name=dish_name,
                category=recipe["category"],
                baseline_portions=base_portions,
                recommended_portions=rec_portions,
                chef_override_portions=override_val,
                portion_size_g=portion_g,
                total_prep_kg=total_kg,
                unit_portion_cost=recipe["unit_portion_cost"],
                historical_scrap_pct=scrap_pct,
                scrap_risk_level=risk_level,
                prep_shifts=shifts,
                expiring_ingredients_used=exp_used
            )

        return orders

    def plan_surplus_dispatch(
        self,
        batch_orders: Dict[str, RecipePrepOrder],
        footfall_actual: int,
        baseline_footfall: int
    ) -> List[SurplusDispatchItem]:
        """
        If diner footfall drops significantly, arms surplus channels to rescue excess food.
        """
        dispatch_items: List[SurplusDispatchItem] = []
        if footfall_actual >= baseline_footfall * 0.90:
            return dispatch_items

        # Footfall drop detected - prepare rescue channels
        drop_ratio = (baseline_footfall - footfall_actual) / max(1, baseline_footfall)

        for r_id, order in batch_orders.items():
            if order.chef_override_portions:
                est_surplus = max(0, order.chef_override_portions - int(order.recommended_portions * (1.0 - drop_ratio)))
            else:
                est_surplus = max(0, int(order.recommended_portions * drop_ratio * 0.40))

            if est_surplus >= 15:
                # Tier 1: Student Flash Sale
                t1_count = int(round(est_surplus * 0.60))
                dispatch_items.append(SurplusDispatchItem(
                    id=f"dsp_{r_id}_flash",
                    tier="TIER_1_FLASH_SALE",
                    badge_label="CAMPUS FLASH SALE (60% OFF)",
                    target_channel="Student Micro-App Broadcast",
                    dish_name=order.dish_name,
                    surplus_portions=t1_count,
                    estimated_pickup_eta="1:45 PM - 2:30 PM",
                    safe_consumption_window_hours=4.0,
                    esg_receipt_id=f"ESG-{uuid.uuid4().hex[:6].upper()}",
                    payload_preview=f"Broadcast: {t1_count} plates of {order.dish_name} at $1.00 via Student App.",
                    status="DISPATCHED"
                ))

                # Tier 2: NGO Food Rescue
                t2_count = est_surplus - t1_count
                if t2_count >= 10:
                    dispatch_items.append(SurplusDispatchItem(
                        id=f"dsp_{r_id}_ngo",
                        tier="TIER_2_NGO_RESCUE",
                        badge_label="FOOD RESCUE NGO DISPATCH",
                        target_channel="Cold-Chain Courier (Robin Hood Army)",
                        dish_name=order.dish_name,
                        surplus_portions=t2_count,
                        estimated_pickup_eta="2:45 PM Insulated Van",
                        safe_consumption_window_hours=6.0,
                        esg_receipt_id=f"ESG-{uuid.uuid4().hex[:6].upper()}",
                        payload_preview=f"Cold-chain transport of {t2_count} sealed portions to local community shelter.",
                        status="DISPATCHED"
                    ))

        return dispatch_items

    def evaluate_chef_override(
        self,
        dish_id: str,
        override_portions: int,
        order: RecipePrepOrder
    ) -> CounterFactualImpact:
        """
        Calculates financial and waste risk if a chef overrides AI recommendations.
        """
        rec = order.recommended_portions
        diff = override_portions - rec

        if diff <= 0:
            return CounterFactualImpact(
                is_active=True,
                overridden_dish=order.dish_name,
                original_recommended=rec,
                chef_manual_portions=override_portions,
                portion_difference=diff,
                financial_risk_usd=0.0,
                excess_scrap_risk_kg=0.0,
                staged_mitigation_plan="Chef scaled down production below AI recommendation. No excess scrap risk."
            )

        # Financial risk
        risk_usd = round(diff * order.unit_portion_cost, 2)
        excess_kg = round((diff * order.portion_size_g) / 1000.0, 1)

        mitigation = (
            f"Chef added +{diff} portions above AI consensus. High overproduction hazard: Projected financial "
            f"exposure +${risk_usd:.2f} ({excess_kg} kg excess). Staged shift intervention triggered: Hold additional "
            f"+{diff} portions in raw marinade until 1:20 PM headcount verifies rush. If turnstile delta remains low, "
            f"route directly to Campus Flash Sale."
        )

        return CounterFactualImpact(
            is_active=True,
            overridden_dish=order.dish_name,
            original_recommended=rec,
            chef_manual_portions=override_portions,
            portion_difference=diff,
            financial_risk_usd=risk_usd,
            excess_scrap_risk_kg=excess_kg,
            staged_mitigation_plan=mitigation
        )

    def generate_log(self, batch_orders: Dict[str, RecipePrepOrder], surplus_count: int, footfall_actual: int = 750) -> AgentLogEntry:
        """Generates the agent log entry with AI reasoning using the API key."""
        loss_func = "L_action = Prep JIT Optimization + Surplus Recovery"
        inputs_summary = f"{len(batch_orders)} menu orders staged in 2 shifts, {surplus_count} surplus channels armed"
        llm_res = self.llm.generate_agent_reasoning(
            self.name, self.role, loss_func, inputs_summary,
            {"footfall": footfall_actual, "details": {k: v.recommended_portions for k, v in batch_orders.items()}}
        )

        return AgentLogEntry(
            id=f"log_action_{datetime.now().strftime('%H%M%S')}",
            timestamp=datetime.now().strftime("%H:%M:%S"),
            agent_name=self.name,
            agent_role=self.role,
            status="DECIDED",
            headline=f"Generated 2-shift cooking schedule for {len(batch_orders)} recipes ({surplus_count} surplus routes armed)",
            reasoning=(
                f"Split prep into Shift 1 (65% at 11:00 AM) and Shift 2 (35% on-demand at 1:15 PM). "
                f"Armed {surplus_count} surplus channels (Flash Sale & NGO rescue) to guarantee zero discarded food."
            ),
            loss_function=loss_func,
            inputs_ingested=[
                f"2-Shift Prep Schedule (65% Base / 35% On-Demand)",
                f"Surplus Dispatch Channels: {surplus_count}",
                f"Production Lines Scheduled: {len(batch_orders)}"
            ],
            detailed_analysis=llm_res["reasoning"],
            llm_source=f"{llm_res['source']} ({llm_res['model']})",
            metrics={
                "production_lines_scheduled": len(batch_orders),
                "shift_split_pct": f"{int(config.SHIFT_1_RATIO*100)}% / {int(config.SHIFT_2_RATIO*100)}%",
                "surplus_channels_armed": surplus_count
            },
            confidence=0.98
        )
