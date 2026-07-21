from __future__ import annotations

import asyncio
from typing import Any

import httpx


FALLBACK_SEGMENTS = [
    (1, "Affluent Investors", 142, 0.72),
    (2, "Emerging Digital Everyday", 188, 0.68),
    (3, "High Spend Credit Active", 164, 0.70),
    (4, "High Spend and Frequent Overdraft", 151, 0.66),
    (5, "Low Digital Engagement and Cash-Oriented", 177, 0.64),
    (6, "Stable Salary Builders", 178, 0.71),
]


class SegmentationClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.is_success and response.json().get("status") == "ok"
        except (httpx.HTTPError, ValueError):
            return False

    async def segments(self) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/v1/segments")
                response.raise_for_status()
                segments = response.json()["segments"]
            customers = await asyncio.gather(
                *(self._customers(int(segment["segment_id"])) for segment in segments)
            )
            return [
                {
                    **segment,
                    "customers": group,
                    "source": "live ML service",
                }
                for segment, group in zip(segments, customers, strict=True)
            ]
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return self._fallback()

    async def _customers(self, segment_id: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"{self.base_url}/v1/customers",
                params={"segment_id": segment_id, "limit": 6},
            )
            response.raise_for_status()
            return response.json().get("customers", [])

    @staticmethod
    def _fallback() -> list[dict[str, Any]]:
        return [
            {
                "segment_id": segment_id,
                "segment_name": name,
                "customer_count": count,
                "average_confidence": confidence,
                "customers": [
                    {
                        "customer_id": f"DEMO-{segment_id}-{index:03d}",
                        "assignment_confidence": round(confidence - index * 0.02, 2),
                    }
                    for index in range(1, 7)
                ],
                "source": "built-in demo fallback",
            }
            for segment_id, name, count, confidence in FALLBACK_SEGMENTS
        ]
