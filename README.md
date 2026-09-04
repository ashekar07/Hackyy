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
