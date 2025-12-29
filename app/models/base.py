"""Shared base classes and helpers for MongoDB documents."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):
    """Pydantic-compatible ObjectId wrapper."""

    @classmethod
    def __get_validators__(cls):  # type: ignore[override]
        yield cls.validate

    @classmethod
    def validate(cls, value: Any, field_info=None) -> "PyObjectId":
        # Accepts (cls, value, field_info) for Pydantic v2 compatibility
        if isinstance(value, ObjectId):
            return cls(value)
        if isinstance(value, str) and ObjectId.is_valid(value):
            return cls(ObjectId(value))
        raise ValueError("Invalid ObjectId")

    @classmethod
    def __get_pydantic_json_schema__(cls, *_) -> dict[str, Any]:  # type: ignore[override]
        return {"type": "string", "pattern": "^[a-fA-F0-9]{24}$"}


class DocumentModel(BaseModel):
    """Base document with shared config for MongoDB collections."""

    id: PyObjectId | None = Field(default=None, alias="_id")
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str, PyObjectId: str},
        "protected_namespaces": (),
    }
