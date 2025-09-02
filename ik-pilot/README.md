# IK‑Pilot (Internet Kartel Pilot)
Your no‑nonsense, Appilot‑style DevOps copilot. FastAPI backend + pluggable tools (Kubernetes, Shell). Human approval toggle.

## Features
- ReAct‑style agent with tool registry
- Kubernetes operations (list pods, get logs, rollout restart)
- Optional shell tool (off by default; enable with `ALLOW_DANGEROUS_TOOLS=true`)
- Human‑in‑the‑loop approvals (default) — disable with `HUMAN_APPROVAL=false`
- OpenAI compatible (supports `OPENAI_API_BASE` / `OPENAI_API_KEY`)

## Quick Start
```bash
# 1) Clone files (you downloaded a zip)
cd ik-pilot

# 2) Python env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3) Configure env
cp .env.example .env
# edit .env to set OPENAI_API_KEY and Kube config path (if needed)

# 4) Run
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 5) Test
curl -s -X POST http://localhost:8000/chat -H 'Content-Type: application/json'   -d '{"message":"List pods in namespace default"}' | jq .
```

## Docker
```bash
docker build -t ik-pilot .
docker run --rm -it -p 8000:8000 --env-file .env ik-pilot
```

## Endpoints
- `POST /chat` → `{ message: str, session_id?: str, force?: bool }`
- `GET /healthz` → health check

## Example Prompts
- "List pods in namespace default"
- "Get logs for deployment api in namespace staging (last 200 lines)"
- "Rollout restart deployment web in namespace production"

## Env Vars
See `.env.example`. Key ones:
- `OPENAI_API_KEY` (required unless using a compatible local model)
- `OPENAI_API_BASE` (optional; Ollama/vLLM/OneAPI)
- `MODEL` (default `gpt-4o-mini`)
- `HUMAN_APPROVAL` (true/false; default true)
- `ALLOW_DANGEROUS_TOOLS` (true/false; default false)
- `KUBECONFIG` (path; optional if cluster creds in env)

## Tests
```bash
pytest -q
```
