"""`get-transactions` `order` accepts common synonyms without weakening the wire contract.

LLMs reliably fill `order` with the everyday synonym a user's phrasing implies
("show my most recent transactions" → `descending`) rather than the canonical
`NewestFirst`. A strict `Literal` rejected those before the handler ran, so the
user saw a failed first tool call and a retry. `TransactionOrderInput` folds the
common synonyms onto the canonical values via a `BeforeValidator`, which does
*not* appear in the advertised schema — so the enum a host/adapter sees stays
exactly `["NewestFirst", "OldestFirst"]`.
"""

import asyncio

import pytest
from pydantic import TypeAdapter, ValidationError

from bank2ai.models import TransactionOrderInput
from bank2ai_demo import server as demo_server


_adapter = TypeAdapter(TransactionOrderInput)


@pytest.mark.parametrize(
    "raw, canonical",
    [
        # canonical values pass through untouched
        ("NewestFirst", "NewestFirst"),
        ("OldestFirst", "OldestFirst"),
        # newest-first synonyms
        ("descending", "NewestFirst"),
        ("DESC", "NewestFirst"),
        ("newest", "NewestFirst"),
        ("most recent", "NewestFirst"),
        ("new-to-old", "NewestFirst"),
        ("  Latest  ", "NewestFirst"),
        # oldest-first synonyms
        ("ascending", "OldestFirst"),
        ("asc", "OldestFirst"),
        ("oldest", "OldestFirst"),
        ("chronological", "OldestFirst"),
        ("old_to_new", "OldestFirst"),
    ],
)
def test_synonyms_fold_onto_canonical(raw, canonical):
    assert _adapter.validate_python(raw) == canonical


@pytest.mark.parametrize("garbage", ["sideways", "random", "", "NewestFirstish"])
def test_unknown_values_still_rejected(garbage):
    with pytest.raises(ValidationError):
        _adapter.validate_python(garbage)


def test_advertised_schema_keeps_the_strict_enum():
    """The BeforeValidator must not leak into the wire contract."""
    tools = {t.name: t for t in asyncio.run(demo_server.app.list_tools())}
    order = tools["get-transactions"].parameters["properties"]["order"]
    assert order["enum"] == ["NewestFirst", "OldestFirst"]
    assert order["default"] == "NewestFirst"


def test_tool_call_accepts_a_synonym_end_to_end():
    """The original bug: a synonym must succeed on the first call, not error."""
    result = asyncio.run(
        demo_server.app.call_tool("get-transactions", {"order": "descending", "count": 3})
    )
    # No exception == the call validated. Sanity-check we actually got data back.
    payload = result.structured_content if hasattr(result, "structured_content") else result
    assert payload is not None
