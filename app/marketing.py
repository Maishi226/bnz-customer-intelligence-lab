from __future__ import annotations

from typing import Any

import httpx


class MarketingClient:
    """Consumes Bedrock-generated campaign versions from bnz-ai-marketing-hybrid."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{self.base_url}/api/health")
                return response.is_success
        except httpx.HTTPError:
            return False

    async def generate(
        self,
        product: str,
        brief: str,
        segments: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], str]:
        outputs: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                for segment in segments:
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "product": product,
                            "brief": brief,
                            "objective": "generate personalised compliant marketing for pre-launch customer testing",
                            "segment_id": int(segment["segment_id"]),
                        },
                    )
                    response.raise_for_status()
                    outputs.extend(response.json().get("campaign", []))
            if not outputs:
                raise ValueError("Marketing service returned no campaign versions")
            return outputs, "bnz-ai-marketing-hybrid · Bedrock"
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return self._fallback(product, segments), "marketing service fallback"

    @staticmethod
    def _fallback(product: str, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "segment_id": segment["segment_id"],
                "segment_name": segment["segment_name"],
                "customer_count": segment.get("customer_count", 0),
                "average_confidence": segment.get("average_confidence", 0),
                "customers": segment.get("customers", []),
                "creative": {
                    "headline": "See the details before you decide",
                    "message": f"Explore {product}. Review the costs, conditions and next steps before deciding.",
                    "cta": "Review in app",
                    "send_reason": "Matched using the behavioural segmentation result.",
                    "bedrock_status": "marketing service unavailable · local placeholder",
                },
            }
            for segment in segments
        ]
