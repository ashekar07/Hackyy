"""
=============================================================================
FOOD WASTE MANAGEMENT - DATA INGESTION & CONVERTER MODULE
=============================================================================
This module reads user-stored data files (recipes, inventory, plate waste logs)
and converts/normalizes them into clean data structures for the AI agents.

How to store your own files:
- Place your files in the 'data/' directory (e.g. recipes.json, inventory.json, waste_logs.json).
- If your files have missing fields, this converter automatically provides safe defaults.
"""
import os
import json
import csv
from typing import Dict, List, Any, Optional

def clean_number(val: Any, default: float = 0.0) -> float:
    """Helper to safely convert any value to float."""
    try:
        if val is None:
            return default
        return float(val)
    except (ValueError, TypeError):
        return default

def clean_int(val: Any, default: int = 0) -> int:
    """Helper to safely convert any value to integer."""
    try:
        if val is None:
            return default
        return int(round(float(val)))
    except (ValueError, TypeError):
        return default

# ---------------------------------------------------------------------------
# 1. Convert Recipe Data
# ---------------------------------------------------------------------------
def convert_recipe(raw_item: Dict[str, Any], index: int = 1) -> Dict[str, Any]:
    """
    Converts a raw user recipe dictionary into a standardized format for agents.
    """
    recipe_id = str(raw_item.get("recipe_id") or raw_item.get("id") or f"rec_custom_{index}")
    dish_name = str(raw_item.get("dish_name") or raw_item.get("name") or f"Custom Dish {index}")
    category = str(raw_item.get("category") or "General Menu")
    default_portions = clean_int(raw_item.get("default_portions") or raw_item.get("portions"), default=200)
    portion_size_g = clean_int(raw_item.get("portion_size_g") or raw_item.get("weight_g"), default=250)
    unit_portion_cost = clean_number(raw_item.get("unit_portion_cost") or raw_item.get("cost"), default=2.0)
    
    # Clean ingredients per portion
    raw_ingredients = raw_item.get("ingredients_per_portion") or raw_item.get("ingredients") or {}
    ingredients: Dict[str, float] = {}
    if isinstance(raw_ingredients, dict):
        for k, v in raw_ingredients.items():
            ingredients[str(k)] = clean_number(v, 0.05)
    elif isinstance(raw_ingredients, list):
        for item in raw_ingredients:
            if isinstance(item, dict) and "ingredient_id" in item:
                ingredients[item["ingredient_id"]] = clean_number(item.get("qty_kg"), 0.05)
            elif isinstance(item, str):
                ingredients[item] = 0.05

    return {
        "recipe_id": recipe_id,
        "dish_name": dish_name,
        "category": category,
        "default_portions": default_portions,
        "portion_size_g": portion_size_g,
        "unit_portion_cost": unit_portion_cost,
        "ingredients_per_portion": ingredients,
        "prep_difficulty": str(raw_item.get("prep_difficulty") or "MEDIUM"),
        "cooking_lead_time_mins": clean_int(raw_item.get("cooking_lead_time_mins"), default=45)
    }

def load_recipes(file_path: str) -> List[Dict[str, Any]]:
    """Loads and converts user recipe file (JSON or CSV)."""
    if not os.path.exists(file_path):
        print(f"[DataLoader] Warning: Recipe file not found at {file_path}, using empty list.")
        return []

    recipes = []
    if file_path.endswith(".json"):
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            items = raw_data if isinstance(raw_data, list) else raw_data.get("recipes", [])
            for idx, item in enumerate(items, start=1):
                recipes.append(convert_recipe(item, idx))
    elif file_path.endswith(".csv"):
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                recipes.append(convert_recipe(row, idx))
    return recipes

# ---------------------------------------------------------------------------
# 2. Convert Inventory Data
# ---------------------------------------------------------------------------
def convert_inventory_item(raw_item: Dict[str, Any], index: int = 1) -> Dict[str, Any]:
    """
    Converts a raw inventory item into a clean format with shelf-life tracking.
    """
    ingredient_id = str(raw_item.get("ingredient_id") or raw_item.get("id") or f"ing_{index}")
    name = str(raw_item.get("name") or raw_item.get("ingredient_name") or f"Ingredient {index}")
    kg_on_hand = clean_number(raw_item.get("kg_on_hand") or raw_item.get("quantity_kg"), default=10.0)
    unit_cost = clean_number(raw_item.get("unit_cost_usd") or raw_item.get("cost_per_kg"), default=3.0)
    shelf_life = clean_number(raw_item.get("shelf_life_hours_remaining") or raw_item.get("hours_left"), default=72.0)
    location = str(raw_item.get("storage_location") or "Main Storage")
    batch = str(raw_item.get("batch_code") or f"LOT-{index:04d}")
    supplier = str(raw_item.get("supplier") or "Standard Supplier")

    return {
        "ingredient_id": ingredient_id,
        "name": name,
        "kg_on_hand": kg_on_hand,
        "unit_cost_usd": unit_cost,
        "shelf_life_hours_remaining": shelf_life,
        "storage_location": location,
        "batch_code": batch,
        "supplier": supplier
    }

def load_inventory(file_path: str) -> List[Dict[str, Any]]:
    """Loads and converts user inventory file (JSON or CSV)."""
    if not os.path.exists(file_path):
        print(f"[DataLoader] Warning: Inventory file not found at {file_path}, using empty list.")
        return []

    inventory = []
    if file_path.endswith(".json"):
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            items = raw_data if isinstance(raw_data, list) else raw_data.get("inventory", [])
            for idx, item in enumerate(items, start=1):
                inventory.append(convert_inventory_item(item, idx))
    elif file_path.endswith(".csv"):
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                inventory.append(convert_inventory_item(row, idx))
    return inventory

# ---------------------------------------------------------------------------
# 3. Convert Waste Logs Data
# ---------------------------------------------------------------------------
def load_waste_logs(file_path: str) -> Dict[str, Any]:
    """
    Loads and converts user waste and plate return logs.
    """
    default_structure = {
        "historical_metrics": {},
        "tray_scanner_vision_audit": {
            "latest_scan_timestamp": "Recent Service",
            "starch_plate_waste_pct": 15.0,
            "protein_plate_waste_pct": 5.0,
            "vegetable_plate_waste_pct": 10.0,
            "ai_vision_confidence": 0.90
        }
    }
    
    if not os.path.exists(file_path):
        print(f"[DataLoader] Warning: Waste log file not found at {file_path}, using defaults.")
        return default_structure

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalize historical metrics
    metrics = data.get("historical_metrics", {})
    clean_metrics: Dict[str, Any] = {}
    for r_id, info in metrics.items():
        clean_metrics[r_id] = {
            "dish_name": str(info.get("dish_name", r_id)),
            "avg_scrap_rate_pct": clean_number(info.get("avg_scrap_rate_pct"), 10.0),
            "tray_return_scrap_g_per_plate": clean_number(info.get("tray_return_scrap_g_per_plate"), 25.0),
            "kitchen_prep_trim_pct": clean_number(info.get("kitchen_prep_trim_pct"), 3.0),
            "risk_tier": str(info.get("risk_tier", "NORMAL")),
            "notes": str(info.get("notes", ""))
        }

    # Normalize vision audit
    raw_vision = data.get("tray_scanner_vision_audit", {})
    clean_vision = {
        "latest_scan_timestamp": str(raw_vision.get("latest_scan_timestamp", "Recent")),
        "starch_plate_waste_pct": clean_number(raw_vision.get("starch_plate_waste_pct"), 15.0),
        "protein_plate_waste_pct": clean_number(raw_vision.get("protein_plate_waste_pct"), 5.0),
        "vegetable_plate_waste_pct": clean_number(raw_vision.get("vegetable_plate_waste_pct"), 10.0),
        "ai_vision_confidence": clean_number(raw_vision.get("ai_vision_confidence"), 0.90)
    }

    return {
        "historical_metrics": clean_metrics,
        "tray_scanner_vision_audit": clean_vision
    }

# ---------------------------------------------------------------------------
# 4. Master Load Function
# ---------------------------------------------------------------------------
def load_all_data(data_dir: str) -> Dict[str, Any]:
    """
    Convenience function: loads and converts all user files from the data directory.
    Returns:
        dict containing 'recipes', 'inventory', and 'waste_logs'.
    """
    recipes_file = os.path.join(data_dir, "recipes.json")
    inventory_file = os.path.join(data_dir, "inventory.json")
    waste_file = os.path.join(data_dir, "waste_logs.json")

    return {
        "recipes": load_recipes(recipes_file),
        "inventory": load_inventory(inventory_file),
        "waste_logs": load_waste_logs(waste_file)
    }
