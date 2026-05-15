"""Shared base class for documented bank2ai models."""

from pydantic import BaseModel, model_serializer


class _Bank2aiModel(BaseModel):
    """Base for documented bank2ai models. Drops None-valued keys on
    serialization so optional fields that are absent on a row don't bloat
    every tool response. The JSON Schema marks these fields optional with
    `default: null`, so omission is conformant; clients must already tolerate
    either form."""

    @model_serializer(mode="wrap")
    def _omit_none(self, handler):
        data = handler(self)
        return {k: v for k, v in data.items() if v is not None}
