"""Amazon Lex V2 fulfillment hook for the Customer Intelligence Lab.

Lex receives the current campaign/simulation as the `simulationContext` session
attribute. This Lambda turns that evidence into a concise, grounded answer.
"""
from __future__ import annotations

import json
import os
from typing import Any

import boto3

def _close(event: dict[str, Any], message: str) -> dict[str, Any]:
    session_state = event.get("sessionState", {})
    intent = session_state.get("intent") or {"name": "CampaignAdvisor"}
    intent["state"] = "Fulfilled"
    return {
        "sessionState": {
            "sessionAttributes": session_state.get("sessionAttributes", {}),
            "dialogAction": {"type": "Close"},
            "intent": intent,
        },
        "messages": [{"contentType": "PlainText", "content": message[:1000]}],
    }


def _local_answer(question: str, context: dict[str, Any]) -> str:
    campaign = context.get("selected_campaign", {})
    summary = context.get("portfolio_summary", {})
    if not campaign:
        return "Run the Lab first so I can answer using the selected campaign and synthetic customer evidence."
    risks = summary.get("top_risks") or campaign.get("recommendations") or []
    if "rewrite" in question.lower() or "improve" in question.lower():
        return f"The safer rewrite is: {campaign.get('safer_rewrite', campaign.get('message', ''))}"
    if "risk" in question.lower() or "why" in question.lower():
        return f"This is {campaign.get('risk_level', 'unrated')} risk. The main evidence is: {'; '.join(risks[:3])}."
    return f"The selected {campaign.get('segment_name', 'audience')} message has readiness {campaign.get('scores', {}).get('readiness', 'not scored')}/100. Review the safer rewrite and material conditions before launch."


def _bedrock_answer(question: str, context: dict[str, Any]) -> str:
    prompt = (
        "You are a concise bank campaign assurance advisor. Answer only from the supplied "
        "synthetic-customer evidence. Never invent rates, approval, eligibility, or personal data. "
        f"Evidence: {json.dumps(context)[:14000]}\nQuestion: {question}"
    )
    client = boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION", "ap-southeast-2"),
    )
    response = client.converse(
        modelId=os.getenv("BEDROCK_ADVISOR_MODEL_ID", "amazon.nova-lite-v1:0"),
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 350, "temperature": 0.25},
    )
    return response["output"]["message"]["content"][0]["text"]


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    session_state = event.get("sessionState", {})
    attributes = session_state.get("sessionAttributes", {})
    try:
        simulation_context = json.loads(attributes.get("simulationContext", "{}"))
    except json.JSONDecodeError:
        simulation_context = {}
    question = event.get("inputTranscript", "").strip()
    try:
        answer = _bedrock_answer(question, simulation_context)
    except Exception:
        answer = _local_answer(question, simulation_context)
    return _close(event, answer)
