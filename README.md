## Foodprint Estimator

A small FastAPI + Streamlit app that uses Google Gemini (2.5 Flash) to infer ingredients for a dish and estimate a simple carbon footprint breakdown.

### Repository layout
- `main.py`: FastAPI backend exposing `/estimate` and `/estimate/image`
- `streamlit_frontend.py`: Streamlit UI (Search and Vision tabs)
- `requirements.txt`: Python dependencies
- `Dockerfile.api`: Backend container
- `Dockerfile.streamlit`: Frontend container
- `docker-compose.yml`: Runs both containers together
- `.dockerignore`: Reduces build context

## How to run

### 1) Clone this repository
Prereqs: Python 3.11+
```
git clone https://github.com/mrohith29/foodprint.git
cd foodprint
```

1. Create `.env` in the repo root:
```
GEMINI_API_KEY=your_key_here
BACKEND_URL=http://localhost:8000
```
2. Install deps:
```
pip install -r requirements.txt
```
3. Start the API:
```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
4. In another terminal, start the Streamlit UI:
```
streamlit run streamlit_frontend.py
```
5. Open the app at `http://localhost:8501`.
   - API docs at `http://localhost:8000/docs`.

### 2) Run with Docker Compose
Prereqs: Docker Desktop, a valid `GEMINI_API_KEY` in your shell or `.env` next to `docker-compose.yml`.

- Make sure images in `docker-compose.yml` are set to your Docker Hub repo. This repo currently uses:
  - `mrohith29/foodprint-api:latest`
  - `mrohith29/foodprint-frontend:latest`



Run:
```
# supply GEMINI_API_KEY in your environment (PowerShell example)
$Env:GEMINI_API_KEY="your_key_here"

docker compose up --build
```
Then open:
- UI: `http://localhost:8501`
- API: `http://localhost:8000/docs`

## API examples

### POST /estimate (JSON body)
Request:
```bash
curl -X POST http://localhost:8000/estimate \
  -H "Content-Type: application/json" \
  -d '{"dish":"Chicken Biryani"}'
```
Response (example):
```json
{
  "dish": "Chicken Biryani",
  "estimated_carbon_kg": 4.2,
  "ingredients": [
    { "name": "Rice", "carbon_kg": 1.1 },
    { "name": "Chicken", "carbon_kg": 2.5 },
    { "name": "Spices", "carbon_kg": 0.2 },
    { "name": "Oil", "carbon_kg": 0.4 }
  ]
}
```

### POST /estimate/image (multipart/form-data)
Request:
```bash
curl -X POST http://localhost:8000/estimate/image \
  -H "Content-Type: multipart/form-data" \
  -F image=@/path/to/dish.jpg
```
Response (example): same shape as above.

## Assumptions and limitations
- **LLM-based estimation**: Emissions are inferred by the model and are heuristic. No authoritative dataset or DB is used.
- **Strict JSON prompting**: The backend asks the model for strict JSON and then parses defensively. If the model returns unexpected text, the API still returns a valid (possibly sparse) structure.
- **Model availability**: The default model is `gemini-2.5-flash`. Your key must have access; otherwise you’ll get a 500 with a helpful message.
- **No persistence**: No database or history is stored.
- **Open CORS**: CORS is open to support local testing and the Streamlit app.

## Design decisions
- **FastAPI + Pydantic models**: Clear, typed request/response contracts; automatic validation and docs (`/docs`).
- **Gemini integration**: Simple wrapper that reads `GEMINI_API_KEY` via `python-dotenv`. A single `GenerativeModel` is created on startup.
- **Defensive JSON parsing**: `safe_parse_json` attempts `json.loads` and then falls back to extracting the first JSON block to avoid brittle responses.
- **Explicit errors over silent fallback**: If the model isn’t configured, return a clear 500 instead of masking with canned values; makes issues visible during setup/deploy.
- **Streamlit UI**: Lightweight, mirrors the two backend flows (text and image) and shows a neat JSON + bullet breakdown.
- **Containers**: Separate Dockerfiles for backend and frontend; a single `requirements.txt` to simplify builds. Compose links services and injects `GEMINI_API_KEY`.

## If taking this to production
- **Security & auth**: Protect endpoints (API keys, OAuth/JWT), lock down CORS, avoid exposing sensitive errors.
- **Rate limiting & quotas**: Prevent abuse and manage LLM costs. Add retry/backoff and circuit-breaking for transient model failures.
- **Observability**: Structured logging (request IDs, latency), metrics (p95, error rates), and tracing.
- **Validation & schemas**: Consider a more rigid schema or structured generation to guarantee JSON shape. Validate numeric ranges.
- **Model management**: Timeouts, retries, fallbacks, and version pinning. Consider a deterministic backend estimator for critical flows.
- **Robust uploads**: Enforce file size/type limits, virus scanning where appropriate, and S3/object storage for larger payloads.
- **Secrets management**: Use a secrets manager (e.g., AWS Secrets Manager), not `.env` files in containers.
- **Performance & scaling**: Container resource requests/limits, autoscaling, and CDN for static assets. Cache frequent results.
- **CI/CD**: Linting, tests, image scanning, SBOM, and automated deploys to your environment.
- **Compliance**: Document data handling and retention, add user-facing disclaimers for heuristic estimates.
