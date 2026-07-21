from __future__ import annotations

import json
import os
import re
from typing import Any

import boto3
from botocore.config import Config


SEGMENT_HINTS = {
    "Affluent Investors": ("confident and concise", "investment activity and strong balances"),
    "Emerging Digital Everyday": ("friendly and low-friction", "frequent mobile banking use"),
    "High Spend Credit Active": ("transparent and control-focused", "active card use"),
    "High Spend and Frequent Overdraft": ("supportive and non-judgemental", "cash-flow pressure signals"),
    "Low Digital Engagement and Cash-Oriented": ("plain and step-by-step", "lower digital engagement"),
    "Stable Salary Builders": ("encouraging and practical", "stable salary inflows"),
}


def _json_from_text(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


class IntelligenceService:
    def __init__(self) -> None:
        self.profile = os.getenv("AWS_PROFILE", "").strip()
        self.region = os.getenv("AWS_REGION", "ap-southeast-2")
        self.model = os.getenv("BEDROCK_EVALUATION_MODEL_ID", "amazon.nova-lite-v1:0")

    @property
    def configured(self) -> bool:
        return bool(self.region and self.model)

    def _client(self):
        session = boto3.Session(
            profile_name=self.profile or None,
            region_name=self.region,
        )
        return session.client(
            "bedrock-runtime",
            region_name=self.region,
            config=Config(connect_timeout=10, read_timeout=180, retries={"max_attempts": 2}),
        )

    def evaluate_campaigns(
        self,
        product: str,
        channel: str,
        timing: str,
        marketing_campaigns: list[dict[str, Any]],
        persona_count: int,
    ) -> dict[str, Any]:
        campaign_context = [
            {
                "segment_id": campaign["segment_id"],
                "segment_name": campaign["segment_name"],
                "headline": campaign.get("creative", {}).get("headline", ""),
                "message": campaign.get("creative", {}).get("message", ""),
                "cta": campaign.get("creative", {}).get("cta", ""),
                "bedrock_rationale": campaign.get("creative", {}).get("send_reason", ""),
            }
            for campaign in marketing_campaigns
        ]
        prompt = f"""
You are the decision engine for a bank pre-launch Customer Intelligence Lab.
The upstream bnz-ai-marketing-hybrid service has already used Amazon Bedrock to create
one advertising version per ML behavioural segment. Do NOT create replacement advertising.
Your only job is to red-team and evaluate each supplied Bedrock advertisement using synthetic personas.

Product/offer: {product}
Channel: {channel}
Timing: {timing}
Bedrock advertising versions to evaluate:
{json.dumps(campaign_context)}

Return ONLY one JSON object with keys "campaigns" and "portfolio_summary".
campaigns must contain exactly one item per supplied advertising version. Each item must contain:
- segment_id (integer), segment_name
- headline, message and cta copied EXACTLY from the supplied Bedrock version
- rationale evaluating why the supplied version may or may not suit that behavioural segment
- personas: exactly {persona_count} diverse synthetic reactions. Each has name, context, reaction, clarity, trust, stress, fairness, accessibility (integer scores 0-100), and risks (array of short strings)
- scores: clarity, trust, stress, fairness, accessibility, readiness (integers 0-100; higher stress means worse, all others higher means better)
- risk_level: Low, Medium, or High
- recommendations: 2-4 precise changes
- safer_rewrite: a materially improved customer-facing message, max 60 words
portfolio_summary must contain readiness (0-100), top_risks (array), and launch_decision (Ready, Revise, or Hold).

Rules:
- Do not claim approval, guaranteed savings, rates, fee status, or eligibility unless explicitly supplied.
- Never expose an internal segment name or targeting label in customer-facing copy.
- Avoid pressure or exclusivity language such as "exclusive access", "act now", or "no strings attached".
- The safer rewrite must directly mitigate the identified risks and must differ materially from an unsafe original.
- Be transparent about customer action, costs, eligibility, and material conditions.
- Do not create sensitive identity labels. Use New Zealand English.
""".strip()
        try:
            response = self._client().converse(
                modelId=self.model,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 5000, "temperature": 0.35},
            )
            output_text = response["output"]["message"]["content"][0]["text"]
            result = _json_from_text(output_text)
            result["ai_status"] = f"Amazon Bedrock evaluation · {self.model}"
            return result
        except Exception as exc:  # Demo must remain usable when an external AI call fails.
            result = self._fallback(product, marketing_campaigns, persona_count)
            result["ai_status"] = f"local fallback · {type(exc).__name__}"
            return result

    @staticmethod
    def _fallback(product: str, marketing_campaigns: list[dict[str, Any]], persona_count: int) -> dict[str, Any]:
        campaigns = []
        persona_templates = [
            ("Jordan", "mobile-first customer", 88, 83, 22, 86, 90),
            ("Aroha", "customer managing a tight weekly budget", 74, 72, 48, 82, 78),
            ("Sam", "customer using assistive technology", 70, 76, 31, 85, 65),
            ("Mere", "customer who prefers plain language", 77, 79, 29, 88, 81),
            ("Taylor", "customer cautious about personalised offers", 69, 61, 44, 73, 80),
            ("Chris", "customer comparing several providers", 81, 75, 28, 84, 84),
            ("Alex", "customer with limited time", 85, 78, 24, 86, 87),
            ("Riley", "customer wanting full cost details", 72, 68, 38, 80, 79),
        ]
        for campaign in marketing_campaigns:
            name = campaign["segment_name"]
            tone, evidence = SEGMENT_HINTS.get(name, ("clear and helpful", "banking behaviour"))
            creative = campaign.get("creative", {})
            message = creative.get("message") or f"Explore {product}. Review the details, costs and next steps before deciding."
            personas = []
            for person, context, clarity, trust, stress, fairness, access in persona_templates[:persona_count]:
                risks = ["Material costs need a prominent link"] if clarity < 80 else []
                personas.append({
                    "name": person,
                    "context": context,
                    "reaction": "Interested, but wants the offer conditions to be easy to verify.",
                    "clarity": clarity,
                    "trust": trust,
                    "stress": stress,
                    "fairness": fairness,
                    "accessibility": access,
                    "risks": risks,
                })
            scores = {
                key: round(sum(p[key] for p in personas) / len(personas))
                for key in ("clarity", "trust", "stress", "fairness", "accessibility")
            }
            scores["readiness"] = round((scores["clarity"] + scores["trust"] + scores["fairness"] + scores["accessibility"] + (100 - scores["stress"])) / 5)
            campaigns.append({
                "segment_id": campaign["segment_id"],
                "segment_name": name,
                "headline": creative.get("headline", "See the details before you decide"),
                "message": message,
                "cta": creative.get("cta", "Review in app"),
                "rationale": f"Evaluated against the segment's {evidence}; the Bedrock version should remain {tone}.",
                "personas": personas,
                "scores": scores,
                "risk_level": "Medium" if scores["readiness"] < 80 else "Low",
                "recommendations": [
                    "Show total cost, fees and eligibility before the CTA.",
                    "Explain why the customer is seeing the message without exposing profiling details.",
                    "Offer a non-digital help route.",
                ],
                "safer_rewrite": message,
            })
        readiness = round(sum(c["scores"]["readiness"] for c in campaigns) / len(campaigns))
        return {
            "campaigns": campaigns,
            "portfolio_summary": {
                "readiness": readiness,
                "top_risks": ["Material conditions may not be prominent", "Personalisation needs a clear explanation"],
                "launch_decision": "Ready" if readiness >= 80 else "Revise",
            },
            "ai_status": "local deterministic fallback",
        }
