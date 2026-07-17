from typing import Literal, Optional

from pydantic import BaseModel, Field


class TriageRequest(BaseModel):
    alert: str = Field(description="Raw security alert text")


class SecurityVerdict(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    src_ip: Optional[str] = Field(None, description="Source IP if present")
    action: Literal["block", "monitor", "ignore", "escalate"]
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(description="Short justification")
