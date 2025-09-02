import json
import asyncio
from typing import Dict, Any, List, Optional, Protocol
import httpx

SYSTEM_PROMPT = """You are IK-Pilot, a decisive DevOps copilot.
- Use tools when needed.
- If an action modifies infrastructure, propose an ACTION PLAN.
- When approval_required=true, stop and return the plan.
- Keep output concise and actionable.
"""

class Tool(Protocol):
    name: str
    description: str
    async def invoke(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]: ...

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    def list_specs(self) -> List[Dict[str, Any]]:
        return [{"name": t.name, "description": t.description} for t in self.tools.values()]

    def get(self, name: str) -> Tool:
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        return self.tools[name]

class Agent:
    def __init__(self, model: str, approval_required: bool, tool_registry: ToolRegistry):
        self.model = model
        self.approval_required = approval_required
        self.tools = tool_registry

    async def _chat(self, api_base: str, headers: Dict[str, str], messages: List[Dict[str, str]]) -> str:
        # Minimal OpenAI-compatible chat call
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{api_base}/chat/completions",
                headers={**headers, "Content-Type": "application/json"},
                json={"model": self.model, "messages": messages, "temperature": 0.2},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def run(self, message: str, session_id: str, api_base: str, headers: Dict[str, str], force: Optional[bool] = None) -> Dict[str, Any]:
        # Ask model for a plan or direct answer with tool usage
        tool_specs = self.tools.list_specs()
        prompt = f"""{SYSTEM_PROMPT}

Tools you can use:
{json.dumps(tool_specs)}

User request: {message}

Respond in strict JSON with fields:
- thought: brief reasoning
- actions: list of objects (tool, action, params) or []
- output: final user-facing answer (if no actions or after executing actions)
"""
        draft = await self._chat(api_base, headers, [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])
        # Ensure JSON
        try:
            plan = json.loads(draft.strip())
        except Exception as e:
            plan = {"thought": "Direct answer.", "actions": [], "output": draft}

        # If actions proposed and approval required (and not force), return plan for confirmation
        if plan.get("actions") and self.approval_required and not force:
            return {"session_id": session_id, "thought": plan.get("thought", ""), "actions": plan["actions"], "output": "APPROVAL_REQUIRED"}

        # Execute actions sequentially
        results = []
        for a in plan.get("actions", []):
            tool = self.tools.get(a["tool"])
            res = await tool.invoke(a["action"], a.get("params", {}))
            results.append({"tool": a["tool"], "result": res})

        # If there were actions, ask model to summarize results
        output = plan.get("output", "")
        if results:
            summary_prompt = f"Summarize the following tool results for the user in 3-6 bullet points:\n{json.dumps(results)}"
            summary = await self._chat(api_base, headers, [
                {"role": "system", "content": "You summarize technical results clearly."},
                {"role": "user", "content": summary_prompt}
            ])
            output = summary

        return {"session_id": session_id, "thought": plan.get("thought", ""), "actions": plan.get("actions", []), "output": output}
