"""
Shared Pydantic Contract for Kitchen Synapse
Defines the unified state passed through the multi-agent DAG and streamed to the UI.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class AgentLogEntry(BaseModel):
    id: str
    timestamp: str
    agent_name: str
    agent_role: str
    status: str      # "THINKING", "DEBATING", "DECIDED", "ALERT", "OVERRIDE"
    headline: str
    reasoning: str
    loss_function: str = "Optimization Loss"
    inputs_ingested: List[str] = Field(default_factory=list)
    detailed_analysis: str = ""
    llm_source: str = "Featherless.ai"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.92

class ArbitrationArgument(BaseModel):
    agent_name: str
    proposed_portions: int
    safety_margin_pct: float
    rationale: str
    priority_level: str  # "HIGH", "CRITICAL", "NORMAL"

class ArbitrationRound(BaseModel):
    dish_id: str
    dish_name: str
    demand_arg: ArbitrationArgument
    waste_arg: ArbitrationArgument
    inventory_arg: ArbitrationArgument
    consensus_portions: int
    compromise_rationale: str
    conflict_intensity: float  # 0.0 to 1.0

class BatchPrepShift(BaseModel):
    shift_id: str
    shift_name: str       # e.g., "Shift 1: 11:00 AM (65% Base)"
    portion_count: int
    prep_kg: float
    action_directive: str # "COOK_NOW" or "HOLD_RAW_CHILLED"
    time_window: str

class RecipePrepOrder(BaseModel):
    recipe_id: str
    dish_name: str
    category: str
    baseline_portions: int
    recommended_portions: int
    chef_override_portions: Optional[int] = None
    portion_size_g: int
    total_prep_kg: float
    unit_portion_cost: float
    historical_scrap_pct: float
    scrap_risk_level: str  # "LOW", "MEDIUM", "CRITICAL"
    prep_shifts: List[BatchPrepShift]
    expiring_ingredients_used: List[str] = Field(default_factory=list)

class CostAndESGMetrics(BaseModel):
    baseline_prep_cost_usd: float
    recommended_prep_cost_usd: float
    avoided_loss_usd: float
    food_saved_kg: float
    co2_prevented_kg: float
    water_conserved_liters: float
    roi_percentage: float

class SurplusDispatchItem(BaseModel):
    id: str
    tier: str              # "TIER_1_FLASH_SALE" | "TIER_2_NGO_RESCUE"
    badge_label: str       # "CAMPUS FLASH SALE (60% OFF)" | "ROBIN HOOD ARMY RESCUE"
    target_channel: str    # "Student Micro-App" | "Cold-Chain Logistics Dispatch"
    dish_name: str
    surplus_portions: int
    estimated_pickup_eta: str
    safe_consumption_window_hours: float
    esg_receipt_id: str
    payload_preview: str
    status: str            # "DISPATCHED" | "PENDING_APPROVAL" | "COMPLETED"

class CounterFactualImpact(BaseModel):
    is_active: bool = False
    overridden_dish: str = ""
    original_recommended: int = 0
    chef_manual_portions: int = 0
    portion_difference: int = 0
    financial_risk_usd: float = 0.0
    excess_scrap_risk_kg: float = 0.0
    staged_mitigation_plan: str = ""

class SimulationScenario(BaseModel):
    scenario_id: str       # "NORMAL", "MONSOON", "EXAM_SURGE", "CHILLER_FAIL"
    title: str
    description: str
    footfall: int
    weather_factor: float
    exam_factor: float
    chiller_status: str

class KitchenState(BaseModel):
    scenario: SimulationScenario
    footfall_actual: int
    footfall_baseline: int
    agent_logs: List[AgentLogEntry] = Field(default_factory=list)
    arbitration_log: List[ArbitrationRound] = Field(default_factory=list)
    batch_orders: Dict[str, RecipePrepOrder] = Field(default_factory=dict)
    cost_esg: CostAndESGMetrics
    surplus_dispatch: List[SurplusDispatchItem] = Field(default_factory=list)
    counter_factual: Optional[CounterFactualImpact] = None
    featherless_info: Dict[str, Any] = Field(default_factory=dict)
    dataset_info: Dict[str, Any] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
