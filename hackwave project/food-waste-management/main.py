"""
FastAPI Server & Real-Time Event Broker for Food Waste Management AI
Serves the Industrial Cyber HUD, REST APIs, and SSE telemetry stream.
"""
import os
import sys
import json
import asyncio
from typing import Dict, Any, Optional

# Reconfigure stdout for Windows console UTF-8 support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

from pipeline import KitchenSynapseEngine, PRESET_SCENARIOS
from config import HOST, PORT

app = FastAPI(title="Food Waste Management AI HUD", version="3.0.0")

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Initialize central engine
engine = KitchenSynapseEngine(data_dir=DATA_DIR)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory queue for Server-Sent Events subscribers
event_subscribers = []

class SimulateRequest(BaseModel):
    scenario_id: Optional[str] = None
    footfall: Optional[int] = None

class OverrideRequest(BaseModel):
    dish_id: str
    portions: int

class DispatchApproveRequest(BaseModel):
    dispatch_id: str

class FeatherlessConfigRequest(BaseModel):
    api_key: str
    model: Optional[str] = None
    verify: bool = False

@app.get("/api/config/featherless")
async def get_featherless_config():
    from llm_client import featherless_client
    return {
        "is_configured": featherless_client.is_configured(),
        "masked_key": featherless_client.get_masked_key(),
        "model": featherless_client.model,
        "base_url": featherless_client.base_url
    }

@app.post("/api/config/featherless")
async def set_featherless_config(req: FeatherlessConfigRequest):
    from llm_client import featherless_client
    if req.verify and req.api_key:
        verification = featherless_client.verify_connection(test_key=req.api_key, test_model=req.model)
        if not verification.get("success"):
            return JSONResponse(status_code=400, content=verification)
    
    featherless_client.set_credentials(req.api_key, req.model)
    # Refresh engine cycle with live Featherless analysis
    if engine.current_state:
        updated_state = engine.run_cycle(
            engine.current_state.scenario,
            custom_footfall=engine.current_state.footfall_actual,
            overrides=engine.active_overrides
        )
        await notify_subscribers({
            "type": "FEATHERLESS_CONFIG_UPDATED",
            "state": updated_state.model_dump()
        })
        return {
            "success": True,
            "message": f"Featherless.ai active with model '{featherless_client.model}'!",
            "masked_key": featherless_client.get_masked_key(),
            "model": featherless_client.model,
            "state": updated_state.model_dump()
        }
    return {"success": True, "message": "Credentials updated successfully"}

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/state")
async def get_state():
    """Returns the current snapshot of the kitchen state."""
    if not engine.current_state:
        engine.run_cycle(PRESET_SCENARIOS["NORMAL"])
    return engine.current_state.model_dump()

@app.post("/api/simulate")
async def simulate_scenario(req: SimulateRequest):
    """
    Triggers dynamic recalculation across all worker agents and arbitration engine.
    """
    scenario = PRESET_SCENARIOS.get(req.scenario_id, engine.current_state.scenario if engine.current_state else PRESET_SCENARIOS["NORMAL"])
    new_state = engine.run_cycle(scenario, custom_footfall=req.footfall)
    
    # Notify active SSE subscribers
    await notify_subscribers({
        "type": "SIMULATION_UPDATE",
        "scenario": scenario.scenario_id,
        "footfall": new_state.footfall_actual,
        "state": new_state.model_dump()
    })
    return new_state.model_dump()

@app.post("/api/override")
async def chef_override(req: OverrideRequest):
    """
    Processes a manual Chef override and evaluates counter-factual financial/spoilage penalty.
    """
    updated_state = engine.apply_chef_override(req.dish_id, req.portions)
    await notify_subscribers({
        "type": "CHEF_OVERRIDE_EVENT",
        "dish_id": req.dish_id,
        "portions": req.portions,
        "counter_factual": updated_state.counter_factual.model_dump() if updated_state.counter_factual else None,
        "state": updated_state.model_dump()
    })
    return updated_state.model_dump()

@app.post("/api/override/reset")
async def reset_overrides():
    """Clears all chef overrides back to AI consensus."""
    updated_state = engine.reset_overrides()
    await notify_subscribers({
        "type": "CHEF_OVERRIDE_RESET",
        "state": updated_state.model_dump()
    })
    return updated_state.model_dump()

@app.post("/api/dispatch/approve")
async def approve_dispatch(req: DispatchApproveRequest):
    """Approves an automated surplus dispatch (NGO or Flash Sale)."""
    assert engine.current_state is not None
    for item in engine.current_state.surplus_dispatch:
        if item.id == req.dispatch_id:
            item.status = "DISPATCHED"
    await notify_subscribers({
        "type": "DISPATCH_APPROVED",
        "dispatch_id": req.dispatch_id,
        "state": engine.current_state.model_dump()
    })
    return {"status": "SUCCESS", "dispatch_id": req.dispatch_id}

class DatasetUpdateRequest(BaseModel):
    dataset_type: str  # "recipes", "inventory", or "waste_logs"
    content: Any

@app.get("/api/dataset")
async def get_dataset():
    """Returns the user-provided datasets currently loaded."""
    return {
        "recipes": engine.recipes,
        "inventory": engine.inventory,
        "waste_logs": engine.waste_logs,
        "counts": {
            "recipes": len(engine.recipes),
            "inventory": len(engine.inventory),
            "waste_logs": len(engine.waste_logs.get("historical_metrics", {}))
        }
    }

@app.post("/api/dataset/reload")
async def reload_dataset():
    """Reloads user files from data/ directory and runs agents on the new dataset."""
    engine.load_data()
    if engine.current_state:
        updated_state = engine.run_cycle(
            engine.current_state.scenario,
            custom_footfall=engine.current_state.footfall_actual,
            overrides=engine.active_overrides
        )
        await notify_subscribers({
            "type": "DATASET_RELOADED",
            "state": updated_state.model_dump()
        })
        return {"success": True, "message": "User dataset reloaded successfully!", "state": updated_state.model_dump()}
    return {"success": True, "message": "User dataset reloaded"}

@app.post("/api/dataset/update")
async def update_dataset(req: DatasetUpdateRequest):
    """Saves user-provided dataset content into data/ and updates agents."""
    file_map = {
        "recipes": os.path.join(DATA_DIR, "recipes.json"),
        "inventory": os.path.join(DATA_DIR, "inventory.json"),
        "waste_logs": os.path.join(DATA_DIR, "waste_logs.json")
    }
    target_path = file_map.get(req.dataset_type)
    if not target_path:
        return JSONResponse(status_code=400, content={"error": f"Unknown dataset type: {req.dataset_type}"})

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(req.content, f, indent=2)

    engine.load_data()
    updated_state = engine.run_cycle(
        engine.current_state.scenario if engine.current_state else PRESET_SCENARIOS["NORMAL"],
        custom_footfall=engine.current_state.footfall_actual if engine.current_state else None,
        overrides=engine.active_overrides
    )
    await notify_subscribers({
        "type": "DATASET_UPDATED",
        "dataset_type": req.dataset_type,
        "state": updated_state.model_dump()
    })
    return {"success": True, "message": f"{req.dataset_type} updated and applied to agents!", "state": updated_state.model_dump()}

async def notify_subscribers(message_dict: Dict[str, Any]):
    """Broadcasts a payload to all connected SSE clients."""
    payload = f"data: {json.dumps(message_dict)}\n\n"
    dead_subscribers = []
    for q in event_subscribers:
        try:
            await q.put(payload)
        except Exception:
            dead_subscribers.append(q)
    for dq in dead_subscribers:
        if dq in event_subscribers:
            event_subscribers.remove(dq)

@app.get("/api/events")
async def sse_stream(request: Request):
    """
    Server-Sent Events endpoint streaming real-time agent thoughts and state updates.
    """
    queue = asyncio.Queue()
    event_subscribers.append(queue)

    async def event_generator():
        # Initial greeting with current state
        if engine.current_state:
            init_msg = json.dumps({
                "type": "INITIAL_CONNECT",
                "state": engine.current_state.model_dump()
            })
            yield f"data: {init_msg}\n\n"
            
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield data
                except asyncio.TimeoutError:
                    # Send keepalive ping comment
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in event_subscribers:
                event_subscribers.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

if __name__ == "__main__":
    import uvicorn
    print(f"[FOOD-WASTE-MANAGEMENT] Starting Server on http://{HOST}:{PORT}...")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
