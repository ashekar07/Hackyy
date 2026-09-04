"""
Automated Verification Suite for Kitchen Synapse Engine
Tests agent loss functions, tension arbitration, deterministic ESG formulas,
and chef counter-factual calculations.
"""
import sys
import os

# Set UTF-8 output encoding for Windows command prompt
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import KitchenSynapseEngine, PRESET_SCENARIOS
from models.state import KitchenState

def run_tests():
    print("==================================================")
    print("[RUNNING] FOOD WASTE MANAGEMENT SYSTEM VERIFICATION")
    print("==================================================")

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    engine = KitchenSynapseEngine(data_dir=data_dir)

    # Test 1: Initial Normal State
    print("\n[TEST 1] Verifying Normal Lunch State...")
    state = engine.run_cycle(PRESET_SCENARIOS["NORMAL"])
    assert isinstance(state, KitchenState), "State must be instance of KitchenState"
    assert len(state.batch_orders) == 4, f"Expected 4 recipes, got {len(state.batch_orders)}"
    assert len(state.arbitration_log) == 4, f"Expected 4 arbitration rounds, got {len(state.arbitration_log)}"
    assert state.cost_esg.baseline_prep_cost_usd > 0, "Baseline cost must be > 0"
    print(f"  OK: Initialized 4 production lines. Total baseline cost: ${state.cost_esg.baseline_prep_cost_usd:.2f}")

    # Test 2: Opposing Objective Functions (Demand vs Waste vs Inventory)
    print("\n[TEST 2] Verifying Agent Loss Functions & Tension Conflict...")
    palak_round = next(r for r in state.arbitration_log if "palak" in r.dish_id.lower())
    print(f"  * Dish: {palak_round.dish_name}")
    print(f"    - Demand Agent proposed: {palak_round.demand_arg.proposed_portions} (wants safety buffer)")
    print(f"    - Waste Agent proposed: {palak_round.waste_arg.proposed_portions} (wants lean cap to stop scrap)")
    print(f"    - Inventory Agent proposed: {palak_round.inventory_arg.proposed_portions} (wants to exhaust expiring paneer)")
    print(f"    - Orchestrator Consensus: {palak_round.consensus_portions} portions (Conflict Intensity: {palak_round.conflict_intensity})")
    
    assert palak_round.demand_arg.proposed_portions > palak_round.waste_arg.proposed_portions, \
        "Demand should propose more than Waste Agent due to safety buffer vs scrap penalty"
    assert palak_round.conflict_intensity > 0.1, "Palak Paneer should exhibit measurable tension"
    print("  OK: Confirmed opposing loss functions and tension arbitration resolution.")

    # Test 3: Deterministic Cost & ESG Math Engine
    print("\n[TEST 3] Verifying Deterministic Math (No Hallucinations)...")
    cost = state.cost_esg
    food_saved = cost.food_saved_kg
    expected_co2 = round(food_saved * 2.5, 1)
    expected_water = round(food_saved * 13.2, 1)
    print(f"  * Food Saved: {food_saved} kg")
    print(f"  * CO2 Prevented: {cost.co2_prevented_kg} kg (Expected: {expected_co2} kg)")
    print(f"  * Water Conserved: {cost.water_conserved_liters} L (Expected: {expected_water} L)")
    assert cost.co2_prevented_kg == expected_co2, "CO2 calculation mismatch!"
    assert cost.water_conserved_liters == expected_water, "Water calculation mismatch!"
    print("  OK: Strict mathematical precision verified.")

    # Test 4: Scenario Presets & Non-Linear Propagation (Monsoon Downpour)
    print("\n[TEST 4] Testing 'Monsoon Downpour' Preset (-44% Footfall)...")
    monsoon_state = engine.run_cycle(PRESET_SCENARIOS["MONSOON"])
    assert monsoon_state.footfall_actual == 420, "Monsoon footfall should be 420"
    biryani_normal = state.batch_orders["rec_chicken_biryani"].recommended_portions
    biryani_monsoon = monsoon_state.batch_orders["rec_chicken_biryani"].recommended_portions
    print(f"  * Chicken Biryani Normal portions: {biryani_normal} -> Monsoon portions: {biryani_monsoon}")
    assert biryani_monsoon < biryani_normal, "Biryani prep should decrease during monsoon!"
    assert len(monsoon_state.surplus_dispatch) > 0, "Surplus channels should arm during monsoon shortfall"
    print(f"  OK: Armed {len(monsoon_state.surplus_dispatch)} surplus dispatch channels (Flash Box + NGO).")

    # Test 5: Chef Override & Counter-Factual Financial Risk Analysis
    print("\n[TEST 5] Testing Chef Override & Counter-Factual Recalculation...")
    override_state = engine.apply_chef_override("rec_chicken_biryani", 550)
    cf = override_state.counter_factual
    assert cf is not None, "Counter-factual impact must be generated"
    assert cf.is_active is True, "Counter-factual must be active"
    print(f"  * Chef Overrode Biryani to 550 portions (AI recommended: {cf.original_recommended})")
    print(f"  * Financial Risk: +${cf.financial_risk_usd:.2f} ({cf.excess_scrap_risk_kg} kg excess)")
    print(f"  * Staged Mitigation: {cf.staged_mitigation_plan[:90]}...")
    assert cf.financial_risk_usd > 0, "Financial risk should be positive for excess portions"
    assert "Hold" in cf.staged_mitigation_plan or "cook" in cf.staged_mitigation_plan.lower(), "Mitigation plan missing!"
    print("  OK: Counter-factual risk and staging mitigation verified.")

    # Reset overrides
    engine.reset_overrides()
    assert engine.current_state.counter_factual is None, "Overrides should be cleanly cleared"
    print("  OK: Overrides reset successfully.")

    print("\n==================================================")
    print("[SUCCESS] ALL 5 PIPELINE INTEGRATION TESTS PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
