import os, subprocess, shlex
from typing import Dict, Any

class ShellTool:
    name = "shell"
    description = "Run shell commands on the host (DANGEROUS). Requires ALLOW_DANGEROUS_TOOLS=true."

    async def invoke(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action != "run":
            raise ValueError("Unsupported action for shell: run")
        cmd = params.get("cmd")
        if not cmd:
            raise ValueError("Missing cmd")
        # Very basic guardrail: refuse obviously destructive wildcards by default
        blocked = ["rm -rf /", ":(){:|:&};:", "mkfs", "dd if="]
        for b in blocked:
            if b in cmd:
                return {"error": f"blocked dangerous pattern: {b}"}
        try:
            completed = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=30)
            return {"returncode": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:]}
        except Exception as e:
            return {"error": str(e)}
