"""
VitaSense AI - Main Backend Application Server
FastAPI Application serving Replay, Benchmark, and Assistant endpoints.
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from vitasense.api.assistant import (
    process_assistant_message,
    check_assistant_health,
    AssistantRequest,
    AssistantResponse,
)
from vitasense.api.replay import (
    list_available_subjects,
    get_replay_stream,
)
from vitasense.api.benchmark import get_benchmark_summary
from vitasense.api.auth import router as auth_router
from vitasense.api.measurements import router as measurements_router

app = FastAPI(
    title="VitaSense AI Telemetry & Benchmark API",
    description="Backend services for Signal Lab replay, benchmark visualization, and safety-aligned assistant.",
    version="1.0.0",
)

# Enable CORS for local web dev and mobile preview
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Phase 2 Authentication & Measurement Ingestion Routers
app.include_router(auth_router)
app.include_router(measurements_router)

from vitasense.api.auth import submit_contact_inquiry, ContactRequest
from fastapi import Request

@app.post("/api/contact", status_code=201)
def api_contact(req: ContactRequest, request: Request):
    """FR-11: Public contact endpoint with rate-limiting."""
    return submit_contact_inquiry(req, request)


@app.get("/api/health")
def api_health():
    return {
        "status": "healthy",
        "service": "VitaSense AI Backend",
        "notice": "REPLAY: public dataset, not live",
    }


@app.get("/api/replay/subjects")
def api_replay_subjects():
    """Lists available PPG-DaLiA subjects cached in data/processed."""
    return list_available_subjects()


@app.get("/api/replay/stream")
def api_replay_stream(
    subject: str = Query("S1", description="Subject ID (S1-S15)"),
    fault: str = Query("NONE", description="Fault type (NONE, F1_GAPS, F2_STALE, F3_DUPL, F4_SPIKE, F5_DRIFT, F6_UNIT, F7_NOISE)"),
    offset: int = Query(0, ge=0, description="Start window index"),
    limit: int = Query(300, ge=10, le=2000, description="Number of windows to return"),
):
    """Streams synchronized PPG HR, ECG Ref HR, Trust Score, and ENMO with synthetic fault toggling."""
    try:
        return get_replay_stream(
            subject=subject,
            fault_type=fault,
            offset=offset,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/benchmark/summary")
def api_benchmark_summary():
    """Returns verified benchmark results from docs/RESULTS_SUMMARY.md."""
    return get_benchmark_summary()


@app.get("/api/assistant/health")
def api_assistant_health():
    """Reports LLM operational status or fallback error category without exposing keys."""
    return check_assistant_health()


@app.post("/api/assistant", response_model=AssistantResponse)
def api_assistant(request: AssistantRequest):
    """
    Assistant endpoint adhering strictly to docs/ASSISTANT_SPEC.md:
    - Intent routing for greetings, data questions, diagnosis refusals, off-topic, prompt injection.
    - Card blocks rendered ONLY upon explicit user request.
    - Answers only from provided context.
    """
    return process_assistant_message(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("vitasense.api.app:app", host="0.0.0.0", port=8000, reload=True)
