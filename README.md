# 🥗 Food Waste Management AI

> A clean, modular, multi-agent AI system designed to eliminate commercial kitchen food waste, reduce ingredient costs, and automate sustainability tracking.

---

## ⚡ Quick Start (In 3 Simple Steps)

### 1. Install Requirements
Open your terminal and run:
```bash
pip install -r requirements.txt
```

### 2. Set Up Your API Key (.env)
A `.env` file is located in the project folder. Open `.env` in any text editor and add your API key:
```env
API_KEY=your_api_key_here
LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
```
*(Note: If you do not provide an API key, the system automatically uses its built-in local engine so you can still run and test everything completely offline!)*

### 3. Run the Application
```bash
python main.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:8000`**

---

## 📂 Project Structure

```text
food-waste-management/
├── .env                  <-- Your API key and settings
├── .env.example          <-- Template configuration
├── requirements.txt      <-- Python dependencies
├── config.py             <-- Loads .env and kitchen thresholds
├── data_loader.py        <-- Ingests & converts files stored by you
├── llm_client.py         <-- AI inference client using .env API key
├── main.py               <-- FastAPI web server & live HUD
├── pipeline.py           <-- Coordinates the 4-step multi-agent cycle
├── test_pipeline.py      <-- Automated verification test suite
├── agents/               <-- Each agent has its own dedicated file!
│   ├── demand_agent.py   <-- Headcount predictor & service safety buffer
│   ├── waste_agent.py    <-- Plate scrap auditor & overprep cutter
│   ├── inventory_agent.py<-- Shelf-life tracker & FIFO perishability defender
│   ├── orchestrator.py   <-- Tension arbitrator & consensus referee
│   ├── cost_agent.py     <-- Financial savings & ESG carbon/water accountant
│   └── action_agent.py   <-- 2-shift prep scheduler & surplus rescue planner
├── data/                 <-- Your custom data files are stored here!
│   ├── recipes.json      <-- Menu recipes, portions, and ingredients
│   ├── inventory.json    <-- Cold storage stock, kg on hand, shelf life
│   └── waste_logs.json   <-- Historical scrap records & tray scanner audit
└── static/               <-- Web interface (HTML/CSS/JS)
```

---

## 📊 How Your Data Is Loaded & Converted (`data_loader.py`)

You can store your own files in the `data/` folder. The system uses **`data_loader.py`** to automatically read, validate, and convert your raw files into clean structures that the agents can use:

1. **`recipes.json`**:
   - Stores your menu items, baseline portion counts, portion size in grams, and ingredient ratios.
   - If any values are missing, the converter provides safe standard defaults.
2. **`inventory.json`**:
   - Stores your pantry and refrigerator stock, lot batch codes, and remaining shelf life in hours.
3. **`waste_logs.json`**:
   - Stores past plate return scrap percentages and tray scanner vision logs.

---

## 🤖 The 6 Agents Explained Simply

Each agent has its **own separate file** in the `agents/` directory, and each agent directly uses the API key from `.env` to explain its decisions:

| Agent File | Role | Plain English Explanation |
| :--- | :--- | :--- |
| **`demand_agent.py`** | *Service Maximizer* | Evaluates expected diners, weather, and exam schedules. Adds a **+8% safety buffer** so the kitchen never runs out of food. |
| **`waste_agent.py`** | *Zero-Waste Purist* | Audits past plate waste logs. Dishes with **>15% historical scrap** get reduced batch sizes to eliminate trash bin dumps. |
| **`inventory_agent.py`** | *Perishability Defender* | Scans ingredients expiring in **< 24 hours** and insists that recipes using them are cooked first (**FIFO: First-In, First-Out**). |
| **`orchestrator.py`** | *Decision Referee* | Resolves conflicts! (Demand wants more, Waste wants less, Inventory wants expiring food). Calculates the optimal compromise. |
| **`cost_agent.py`** | *Cost & ESG Accountant* | Computes direct dollar savings, kg of food saved, and environmental offsets (**2.5 kg CO2e / kg food saved**, **13.2 L water / kg saved**). |
| **`action_agent.py`** | *Prep Scheduler & Surplus* | Splits daily cooking into **Shift 1 (65% at 11:00 AM)** and **Shift 2 (35% at 1:15 PM)**. Routes leftovers to student flash sales or charity NGOs. |

---

## 🧪 Running Automated Tests

To test the entire pipeline, run:
```bash
python test_pipeline.py
```
This tests:
1. Normal cycle initialization and portion calculations.
2. Opposing agent loss functions (Demand vs Waste vs Inventory).
3. Exact mathematical precision for cost and carbon offsets.
4. Weather drop scenario (Monsoon simulation).
5. Counter-factual risk calculation when a chef manually overrides AI recommendations.

## System Overview

FoodWise AI combines a FastAPI backend, a browser dashboard, a multi-agent planning pipeline, editable JSON datasets, and SMTP notifications for surplus redistribution.

The planning cycle works as follows:

1. `data_loader.py` loads and normalizes recipes, inventory, and waste logs.
2. Demand, waste, and inventory agents independently propose portions.
3. `orchestrator.py` resolves the competing recommendations into a consensus.
4. `action_agent.py` creates the two-shift preparation plan and surplus channels.
5. `cost_agent.py` calculates financial and environmental metrics.
6. The resulting `KitchenState` is returned to the dashboard and streamed through SSE.

The default rules include an 8% demand safety buffer, a 15% high-scrap threshold, a 24-hour expiry alert window, a 65/35 cooking split, 2.5 kg CO2 avoided per kg of food saved, and 13.2 liters of water conserved per kg saved.

## Repository Layout

```text
hackwave project/
├── requirements.txt                 Python dependencies
├── .env                             Local secrets and settings
└── food-waste-management/
      ├── main.py                      FastAPI application and HTTP routes
      ├── config.py                    Environment variables and operating constants
      ├── pipeline.py                  Multi-agent planning and state orchestration
      ├── data_loader.py               JSON dataset loading and normalization
      ├── llm_client.py                Optional Featherless-compatible client
      ├── mail_service.py              SMTP delivery for surplus notifications
      ├── test_pipeline.py             Integration verification suite
      ├── agents/                      Demand, waste, inventory, action, cost, and orchestrator agents
      ├── models/state.py              Pydantic contracts shared by agents and UI
      ├── data/                        Recipes, inventory, and waste-log JSON files
      └── static/                      Dashboard HTML, JavaScript, and CSS
```

## Quick Start

From the repository root, open PowerShell and run:

```powershell
cd "hackwave project\food-waste-management"
python -m pip install -r requirements.txt
python main.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The server defaults to `127.0.0.1:8000`; set `HOST` and `PORT` in `.env` to change it.

## Configuration

The application loads `hackwave project/.env` automatically. A typical configuration is:

```env
HOST=127.0.0.1
PORT=8000

# Optional LLM integration. The local rule engine is used when this is empty.
API_KEY=your_api_key_here
LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
LLM_BASE_URL=https://api.featherless.ai/v1

# SMTP notifications for surplus redistribution.
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-account@gmail.com
SMTP_PASSWORD=your-google-app-password
SMTP_FROM=your-account@gmail.com
MANAGER_EMAIL=manager@example.com
```

For Gmail, enable two-step verification and use a Google App Password for `SMTP_PASSWORD`, not the normal account password. Keep `.env` local and never publish API keys or SMTP credentials.

## HTTP API

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/` | Serves the dashboard |
| `GET` | `/api/state` | Returns the current kitchen state |
| `POST` | `/api/simulate` | Runs a scenario or custom footfall calculation |
| `POST` | `/api/override` | Applies a chef portion override |
| `POST` | `/api/override/reset` | Clears chef overrides |
| `GET` | `/api/events` | Streams updates over Server-Sent Events |
| `GET` | `/api/dataset` | Returns loaded datasets and counts |
| `POST` | `/api/dataset/update` | Saves and applies a dataset update |
| `POST` | `/api/dataset/reload` | Reloads datasets from disk |
| `GET` | `/api/config/featherless` | Shows LLM configuration status |
| `POST` | `/api/config/featherless` | Updates and optionally verifies LLM credentials |
| `POST` | `/api/dispatch/approve` | Marks a surplus item as dispatched |
| `POST` | `/api/dispatch/redistribute` | Emails the manager about surplus meals |

The dashboard calls these routes automatically. Redistribution email includes the selected route and number of meals. Failed delivery returns HTTP `502` with an error instead of reporting a false success.

## Scenarios

Built-in scenarios are defined in `pipeline.py`:

- `NORMAL`: standard kitchen conditions.
- `MONSOON`: reduced footfall caused by heavy rain.
- `EXAM_SURGE`: increased demand during examinations.
- `CHILLER_FAIL`: cold-storage failure requiring urgent inventory decisions.

Example request:

```powershell
Invoke-RestMethod -Method Post `
   -Uri http://127.0.0.1:8000/api/simulate `
   -ContentType 'application/json' `
   -Body '{"scenario_id":"MONSOON"}'
```

## Data Files

Edit the JSON files in `food-waste-management/data/`, then use the dashboard reload control or call `POST /api/dataset/reload`.

- `recipes.json` defines dishes, baseline portions, portion size, ingredients, and unit cost.
- `inventory.json` defines available stock, lot identifiers, and remaining shelf life.
- `waste_logs.json` defines historical scrap percentages and waste observations.

Keep the existing field names and JSON structure when adding records so the loader and agents can process them correctly.

## Testing

Run the verification suite from the application directory:

```powershell
cd "hackwave project\food-waste-management"
python test_pipeline.py
```

The suite checks normal planning, agent disagreement, ESG calculations, the monsoon scenario, and chef override risk calculations.

## Troubleshooting

### The dashboard does not load

Confirm the server is running from `food-waste-management` and browse to `http://127.0.0.1:8000`. Check that the selected Python interpreter has the packages from `requirements.txt` installed.

### LLM reasoning is unavailable

The application continues with local rule-based reasoning. Check `API_KEY`, `LLM_BASE_URL`, and the model name only when live LLM reasoning is required.

### Email delivery fails

Check that all SMTP variables are set, the SMTP port is `587`, the account allows authenticated SMTP, and Gmail uses an App Password. The server returns the delivery error in its response.

## Security Notes

- Never commit `.env`, API keys, SMTP passwords, or manager email data.
- Keep the development server bound to `127.0.0.1` unless network access is intentional.
- Add authentication and authorization before exposing the API outside a trusted local network.
