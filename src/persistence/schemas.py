from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CodeMappingResponse(BaseModel):
    id: int
    cnmc_code: str
    source_cpse: str
    original_code: str

    model_config = ConfigDict(from_attributes=True)


class CNMCResponse(BaseModel):
    cnmc_code: str
    canonical_description: str
    confidence_at_merge: float
    merge_type: str
    created_at: datetime
    mappings: list[CodeMappingResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    entry_id: int
    cnmc_code: str | None
    action: str
    actor: str
    details: dict[str, Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)