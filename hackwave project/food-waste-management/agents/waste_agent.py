"""
=============================================================================
WASTE AGENT - Zero-Waste Purist & Scrap Outlier Detector
=============================================================================
Goal:
- Audits historical plate waste, tray scanner data, and prep trimmings.
- Penalizes dishes that exceed the 15% scrap threshold by reducing batch size.

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

class WasteAgent:
    """
    Minimizes food scrap and plate waste by proposing lean batch sizes.
    """
    def __init__(self, api_key: str = None):
        self.name = "Waste Agent"
        self.role = "Zero-Waste Purist & Scrap Outlier Detector"
        # API key loaded from .env file
        self.api_key = api_key or config.API_KEY
        self.llm = LLMClient(api_key=self.api_key)

    def analyze(
        self,
        recipes: List[Dict[str, Any]],
        waste_logs: Dict[str, Any],
        footfall_actual: int,
        weather_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Step 1: Check historical scrap rates from converted waste logs.
        Step 2: Propose reduced portion sizes for high-waste dishes.
        Step 3: Generate AI reasoning using the API key from .env.
        """
        footfall_ratio = footfall_actual / max(1, config.BASELINE_CAMPUS_FOOTFALL)
        historical = waste_logs.get("historical_metrics", {})
        vision_audit = waste_logs.get("tray_scanner_vision_audit", {})
        
        arguments: Dict[str, ArbitrationArgument] = {}
        proposed_portions: Dict[str, int] = {}
        high_risk_dishes: List[str] = []

        for recipe in recipes:
            r_id = recipe["recipe_id"]
            dish_name = recipe["dish_name"]
            base_portions = recipe["default_portions"]
            
            # Baseline scaled by footfall
            scaled_base = base_portions * footfall_ratio * weather_factor
            
            dish_stats = historical.get(r_id, {})
            scrap_rate = dish_stats.get("avg_scrap_rate_pct", 10.0)
            
            # If scrap exceeds high scrap threshold (15%), cut batch size
            if scrap_rate > config.HIGH_SCRAP_THRESHOLD_PCT:
                scrap_penalty = (scrap_rate - config.HIGH_SCRAP_THRESHOLD_PCT) * 1.6
                lean_multiplier = max(0.60, (100.0 - scrap_penalty) / 100.0)
                lean_portions = int(round(scaled_base * lean_multiplier))
                high_risk_dishes.append(f"{dish_name} ({scrap_rate:.1f}% scrap)")
                priority = "CRITICAL"
                rationale = (
                    f"CRITICAL SCRAP WARNING: Historical scrap is {scrap_rate:.1f}% (above {config.HIGH_SCRAP_THRESHOLD_PCT}% cap). "
                    f"Insisting on lean cap of {lean_portions} portions to eliminate tray return dump."
                )
            else:
                # Normal dish: conservative lean ceiling (-5% buffer)
                lean_multiplier = 0.95
                lean_portions = int(round(scaled_base * lean_multiplier))
                priority = "NORMAL"
                rationale = (
                    f"Moderate scrap history ({scrap_rate:.1f}%). Recommending conservative batch of {lean_portions} "
                    f"to prevent warming-pan dryout."
                )
            
            # Check vision audit for high starch discard
            if "Biryani" in dish_name and vision_audit.get("starch_plate_waste_pct", 0) > 20:
                lean_portions = int(round(lean_portions * 0.92))
                rationale += f" [Vision Alert: Recent trays showed {vision_audit['starch_plate_waste_pct']}% starch discard]."

            lean_portions = max(15, lean_portions)
            proposed_portions[r_id] = lean_portions
            arguments[r_id] = ArbitrationArgument(
                agent_name=self.name,
                proposed_portions=lean_portions,
                safety_margin_pct=round((lean_multiplier - 1.0) * 100, 1),
                rationale=rationale,
                priority_level=priority
            )

        # Generate intelligent reasoning using API key
        loss_func = "L_waste = Historical Plate Scrapings + Preparation Trimmings"
        inputs_summary = f"{len(high_risk_dishes)} high-scrap dishes flagged, threshold {config.HIGH_SCRAP_THRESHOLD_PCT}%"
        llm_res = self.llm.generate_agent_reasoning(
            self.name, self.role, loss_func, inputs_summary,
            {"footfall": footfall_actual, "details": proposed_portions}
        )

        log = AgentLogEntry(
            id=f"log_waste_{footfall_actual}",
            timestamp=datetime.now().strftime("%H:%M:%S"),
            agent_name=self.name,
            agent_role=self.role,
            status="ALERT" if high_risk_dishes else "DECIDED",
            headline=(
                f"Flagged {len(high_risk_dishes)} recipes exceeding {config.HIGH_SCRAP_THRESHOLD_PCT}% scrap threshold"
                if high_risk_dishes else "Scrap risk within tolerable boundary"
            ),
            reasoning=(
                f"Evaluated plate return telemetry and AI tray scanner. "
                f"Flagged for batch reduction: {', '.join(high_risk_dishes) if high_risk_dishes else 'None'}."
            ),
            loss_function=loss_func,
            inputs_ingested=[
                f"Scrap records for {len(recipes)} recipes",
                f"High-Scrap Threshold: {config.HIGH_SCRAP_THRESHOLD_PCT}%",
                f"High-Risk Items Count: {len(high_risk_dishes)}"
            ],
            detailed_analysis=llm_res["reasoning"],
            llm_source=f"{llm_res['source']} ({llm_res['model']})",
            metrics={
                "high_scrap_items_count": len(high_risk_dishes),
                "threshold_enforced_pct": config.HIGH_SCRAP_THRESHOLD_PCT,
                "dishes_flagged": high_risk_dishes
            },
            confidence=0.95
        )

        return {
            "proposed_portions": proposed_portions,
            "arguments": arguments,
            "log": log
        }
