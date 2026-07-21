from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from app.intelligence import IntelligenceService  # noqa: E402
from app.lex import LexService  # noqa: E402
from app.marketing import MarketingClient  # noqa: E402
from app.models import CampaignRequest, ChatRequest  # noqa: E402
from app.segmentation import SegmentationClient  # noqa: E402


segmentation = SegmentationClient(os.getenv("SEGMENTATION_SERVICE_URL", "http://127.0.0.1:8000"))
marketing = MarketingClient(os.getenv("MARKETING_SERVICE_URL", "http://127.0.0.1:8010"))
intelligence = IntelligenceService()
lex = LexService()

app = FastAPI(title="BNZ Customer Intelligence Lab", version="1.0.0")
app.mount("/assets", StaticFiles(directory=ROOT / "frontend"), name="assets")


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "segmentation": "live" if await segmentation.health() else "fallback",
        "marketing_bedrock": "live" if await marketing.health() else "fallback",
        "openai": "configured" if intelligence.configured else "fallback",
        "openai_model": intelligence.model,
        "lex": "configured" if lex.configured else "placeholder",
        "lambda": "invoked by Lex fulfillment when configured",
    }


@app.get("/api/segments")
async def get_segments() -> dict[str, Any]:
    return {"segments": await segmentation.segments()}


@app.post("/api/campaigns")
async def create_campaign(request: CampaignRequest) -> dict[str, Any]:
    all_segments = await segmentation.segments()
    selected = [
        segment for segment in all_segments
        if not request.segment_ids or int(segment["segment_id"]) in request.segment_ids
    ][:6]
    if not selected:
        raise HTTPException(status_code=404, detail="No selected segment exists")
    bedrock_campaigns, marketing_source = await marketing.generate(
        request.product,
        request.brief,
        selected,
    )
    result = await asyncio.to_thread(
        intelligence.evaluate_campaigns,
        request.product,
        request.channel,
        request.timing,
        bedrock_campaigns,
        request.persona_count,
    )
    campaign_lookup = {int(campaign["segment_id"]): campaign for campaign in bedrock_campaigns}
    for campaign in result.get("campaigns", []):
        upstream = campaign_lookup.get(int(campaign["segment_id"]), {})
        campaign["audience"] = {
            "customer_count": upstream.get("customer_count", 0),
            "average_confidence": upstream.get("average_confidence", 0),
            "sample_customer_ids": [c.get("customer_id") for c in upstream.get("customers", [])],
            "source": marketing_source,
        }
        campaign["bedrock_status"] = upstream.get("creative", {}).get("bedrock_status", marketing_source)
    result["pipeline"] = {
        "segmentation": "bank-segmentation-service",
        "generation": marketing_source,
        "evaluation": result.get("ai_status", "Customer Intelligence Lab"),
    }
    return result


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, str]:
    try:
        return await asyncio.to_thread(lex.chat, request.message, request.session_id, request.context)
    except Exception as exc:
        return {
            "reply": "The Lex connection is unavailable. Check AWS credentials, bot alias, locale and Lambda permissions.",
            "source": f"Lex error · {type(exc).__name__}",
        }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT / "frontend" / "index.html")
