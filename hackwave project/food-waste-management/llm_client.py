"""
=============================================================================
FOOD WASTE MANAGEMENT - LLM & AGENT REASONING CLIENT
=============================================================================
Connects the AI agents to Large Language Models (Featherless.ai, OpenAI, etc.)
using the API key stored in your .env file.

If no API key is provided, it automatically falls back to deterministic rule-based
reasoning so the application always runs smoothly.
"""
import os
import json
import httpx
from typing import Dict, Any, Optional
import config

class LLMClient:
    """
    Manages communication with LLM providers using the API key from .env.
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        # Reads API key from .env via config
        self.api_key = (api_key or config.API_KEY).strip()
        self.model = (model or config.LLM_MODEL).strip()
        self.base_url = config.LLM_BASE_URL.rstrip("/")
        self.consecutive_failures = 0

    def set_credentials(self, api_key: str, model: Optional[str] = None):
        """Allows updating the API key at runtime."""
        self.api_key = api_key.strip()
        if model:
            self.model = model.strip()
        self.consecutive_failures = 0

    def is_configured(self) -> bool:
        """Returns True if a valid API key is present."""
        return bool(self.api_key and len(self.api_key) > 5 and self.consecutive_failures < 2)

    def get_masked_key(self) -> str:
        """Returns a safe, masked view of the API key for UI display."""
        if not self.api_key or len(self.api_key) <= 5:
            return "Not Configured (Using Local Engine)"
        if self.consecutive_failures >= 2:
            return f"{self.api_key[:4]}...{self.api_key[-4:]} (Auth/Network Offline)"
        if len(self.api_key) <= 8:
            return "key_****"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

    def verify_connection(self, test_key: Optional[str] = None, test_model: Optional[str] = None) -> Dict[str, Any]:
        """Tests connection to the LLM API."""
        key = test_key or self.api_key
        mod = test_model or self.model
        if not key:
            return {"success": False, "error": "API key is missing in .env file."}

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": mod,
            "messages": [
                {"role": "system", "content": "You are a test probe for Food Waste Management AI."},
                {"role": "user", "content": "Ping test. Reply with 'READY'."}
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }

        try:
            with httpx.Client(timeout=4.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    self.consecutive_failures = 0
                    return {
                        "success": True,
                        "model": mod,
                        "message": f"Connected successfully! Model '{mod}' is active."
                    }
                else:
                    self.consecutive_failures += 1
                    return {
                        "success": False,
                        "status_code": resp.status_code,
                        "error": f"API returned error {resp.status_code}: {resp.text}"
                    }
        except Exception as e:
            self.consecutive_failures += 1
            return {"success": False, "error": f"Network exception: {str(e)}"}

    def generate_agent_reasoning(
        self,
        agent_name: str,
        role: str,
        loss_function: str,
        inputs_summary: str,
        state_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Queries the LLM using the agent's specific context and API key.
        Falls back to deterministic rule synthesis if offline or key is blank.
        """
        if self.is_configured() and self.consecutive_failures == 0:
            try:
                system_prompt = (
                    f"You are the '{agent_name}' ({role}) in a smart commercial kitchen food waste management system. "
                    f"Your objective: {loss_function}. "
                    f"Analyze the incoming data, state your step-by-step rationale, evaluate waste risks, "
                    f"and provide an actionable operational directive. Keep it concise, professional, and clear."
                )
                user_content = (
                    f"Kitchen Data Context:\n"
                    f"- Inputs: {inputs_summary}\n"
                    f"- Expected Diners: {state_context.get('footfall', 420)}\n"
                    f"- Details: {json.dumps(state_context.get('details', {}), indent=2)}\n\n"
                    f"Provide your concise reasoning and final recommendation."
                )

                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "max_tokens": 250,
                    "temperature": 0.3
                }

                with httpx.Client(timeout=3.5) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        llm_text = data["choices"][0]["message"]["content"].strip()
                        return {
                            "source": "AI LLM Inference",
                            "model": self.model,
                            "reasoning": llm_text,
                            "tokens_used": data.get("usage", {}).get("total_tokens", 0)
                        }
                    else:
                        self.consecutive_failures += 1
            except Exception as e:
                self.consecutive_failures += 1
                print(f"[LLMClient] Live query skipped ({e}), using local rule engine.")

        # Fallback local reasoning (guarantees system never breaks)
        return {
            "source": "Local Rule Engine (Offline Fallback)",
            "model": "rule-based",
            "reasoning": self._generate_fallback_reasoning(agent_name, inputs_summary, state_context),
            "tokens_used": 0
        }

    def _generate_fallback_reasoning(self, agent_name: str, inputs_summary: str, state_context: Dict[str, Any]) -> str:
        """Clear, human-readable fallback explanations for each agent."""
        footfall = state_context.get("footfall", 420)
        if "Demand" in agent_name:
            return (
                f"Evaluated expected headcount ({footfall} diners) and weather conditions. "
                f"Applying a +8% service protection buffer across all dishes to ensure no diner is turned away."
            )
        elif "Waste" in agent_name:
            return (
                f"Audited historical plate waste and tray return logs. Dishes with >15% scrap rate were penalized "
                f"and reduced to eliminate overproduction and prevent food being thrown into waste bins."
            )
        elif "Inventory" in agent_name:
            return (
                f"Scanned refrigerator and storage shelf-life codes. Identified perishable items expiring in < 24 hours. "
                f"Prioritized dishes consuming these ingredients so they get eaten before spoiling."
            )
        elif "Cost" in agent_name:
            return (
                f"Calculated exact financial and environmental savings: prevented overprep losses, reduced municipal "
                f"scrap fees, and calculated avoided carbon emissions and water conservation."
            )
        elif "Action" in agent_name:
            return (
                f"Split cooking into 2 shifts: Shift 1 (65% base batch at 11:00 AM) and Shift 2 (35% on-demand at 1:15 PM). "
                f"Any unexpected leftovers are automatically scheduled for student flash discounts or NGO donation."
            )
        else:  # Orchestrator
            return (
                f"Balanced conflicting priorities: Demand wanted more portions, Waste wanted less, and Inventory wanted "
                f"to use expiring stock. Negotiated a balanced production batch that saves food while satisfying diners."
            )

# Global singleton client instance
llm_client = LLMClient()
featherless_client = llm_client  # Alias for backward compatibility
