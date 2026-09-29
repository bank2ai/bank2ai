"""The `domestic-SE` rail, the `other` account identifier and the `swish`
alias type (spec proposal targeting 0.21.0-draft).

Three layers: the Pydantic models, the committed JSON spec, and the demo
server's tools called through FastMCP, so the MCP input schema is
exercised the way a client hits it.

Example values are synthetic: the giro numbers only carry valid check
digits, `1231181189` is Swish's published test merchant number, and
`+46701740605` is in the range the Swedish telecom regulator (PTS)
reserves for fiction. The IBAN / BBAN pair is the IBAN registry's
Swedish example.
"""

import asyncio
import json
from pathlib import Path

import pytest
from fastmcp.exceptions import ToolError
from pydantic import TypeAdapter, ValidationError

from bank2ai import (
    AccountIdentifier,
    AccountNumberIdentifier,
    AliasIdentifier,
    AliasType,
    BbanIdentifier,
    IbanIdentifier,
    OtherIdentifier,
    Rail,
)
from bank2ai_demo import server as demo_server


REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC = json.loads((REPO_ROOT / "specs" / "bank2ai.json").read_text())

IDENTIFIER = TypeAdapter(AccountIdentifier)

BANKGIRO = {"type": "other", "identifier": "1234-5674", "schemeName": "BGNR", "country": "SE"}
PLUSGIRO = {"type": "other", "identifier": "12 34 56-6", "schemeName": "PGNR", "country": "SE"}
SWISH_NUMBER = {"type": "alias", "alias": "1231181189", "aliasType": "swish"}
SWISH_PHONE = {"type": "alias", "alias": "+46701740605", "aliasType": "phone"}
SE_BBAN = {"type": "bban", "bban": "50000000058398257466", "country": "SE"}
SE_IBAN = {"type": "iban", "iban": "SE4550000000058398257466"}


def _tool(name: str) -> dict:
    return next(t for t in SPEC["tools"] if t["name"] == name)


def _variant_types(union: dict) -> list[str]:
    members = union.get("oneOf") or union.get("anyOf") or []
    return [m["properties"]["type"]["const"] for m in members if "properties" in m]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

def test_rail_domestic_se():
    assert Rail("domestic-SE") is Rail.DomesticSE


@pytest.mark.parametrize("payload", [BANKGIRO, PLUSGIRO])
def test_other_identifier_round_trips(payload):
    parsed = IDENTIFIER.validate_python(payload)
    assert isinstance(parsed, OtherIdentifier)
    assert IDENTIFIER.dump_python(parsed, mode="json") == payload


@pytest.mark.parametrize(
    "broken",
    [
        {k: v for k, v in BANKGIRO.items() if k != "schemeName"},
        {k: v for k, v in BANKGIRO.items() if k != "country"},
        {k: v for k, v in BANKGIRO.items() if k != "identifier"},
        {**BANKGIRO, "country": "se"},
    ],
    ids=["no-scheme-name", "no-country", "no-identifier", "lowercase-country"],
)
def test_other_identifier_rejects_incomplete_input(broken):
    with pytest.raises(ValidationError):
        IDENTIFIER.validate_python(broken)


@pytest.mark.parametrize(
    "payload, model",
    [
        (SE_IBAN, IbanIdentifier),
        (SE_BBAN, BbanIdentifier),
        (
            {"type": "accountNumber", "accountNumber": "5678-90-123457", "country": "US",
             "routing": "021000021"},
            AccountNumberIdentifier,
        ),
        ({"type": "alias", "alias": "alex@upi", "aliasType": "vpa"}, AliasIdentifier),
    ],
    ids=["iban", "bban", "accountNumber", "alias"],
)
def test_existing_identifier_variants_unchanged(payload, model):
    parsed = IDENTIFIER.validate_python(payload)
    assert isinstance(parsed, model)
    assert IDENTIFIER.dump_python(parsed, mode="json") == payload


def test_swish_alias_type():
    parsed = IDENTIFIER.validate_python(SWISH_NUMBER)
    assert isinstance(parsed, AliasIdentifier)
    assert parsed.aliasType is AliasType.Swish


# ---------------------------------------------------------------------------
# Committed spec (specs/bank2ai.json)
# ---------------------------------------------------------------------------

def test_spec_rail_enum_is_additive():
    rail = _tool("prepare-transfer")["inputSchema"]["properties"]["rail"]
    assert rail["enum"] == ["domestic-IS", "domestic-SE", "sepa", "sepa-instant", "swift"]


def test_spec_publishes_other_identifier():
    component = SPEC["componentSchemas"]["OtherIdentifier"]
    assert component["properties"]["type"]["const"] == "other"
    assert set(component["required"]) == {"identifier", "schemeName", "country"}

    account_identifier = _tool("create-recipient")["inputSchema"]["properties"]["account_identifier"]
    assert _variant_types(account_identifier) == ["iban", "bban", "accountNumber", "alias", "other"]

    recipient = SPEC["models"]["Recipient"]
    mapping = recipient["properties"]["accountIdentifier"]["discriminator"]["mapping"]
    assert mapping["other"] == "#/$defs/OtherIdentifier"
    assert "swish" in recipient["$defs"]["AliasType"]["enum"]


# ---------------------------------------------------------------------------
# Demo server, through the MCP tool surface
# ---------------------------------------------------------------------------

def _prepare(creditor_identifier: dict, rail: str, **extra) -> dict:
    result = asyncio.run(demo_server.app.call_tool("prepare-transfer", {
        "debtor_account_id": "acc_checking_001",
        "creditor": {"name": "Exempel AB", "accountIdentifier": creditor_identifier},
        "amount": 250.0,
        "currency": "SEK",
        "rail": rail,
        **extra,
    }))
    payload = result.structured_content
    assert payload.get("code") is None, payload["content"]
    return payload["item"]["summary"]


@pytest.mark.parametrize(
    "creditor_identifier, instrument",
    [
        (BANKGIRO, "BANKGIRO"),
        (PLUSGIRO, "PLUSGIRO"),
        (SWISH_NUMBER, "SWISH"),
        (SWISH_PHONE, "SWISH"),
    ],
    ids=["bankgiro", "plusgiro", "swish-number", "swish-phone"],
)
def test_domestic_se_derives_instrument_from_identifier(creditor_identifier, instrument):
    summary = _prepare(creditor_identifier, "domestic-SE")
    assert summary["rail"] == "domestic-SE"
    assert summary["localInstrument"] == instrument
    assert summary["creditor"]["accountIdentifier"] == creditor_identifier


def test_domestic_se_account_transfer_has_no_derived_instrument():
    summary = _prepare(SE_BBAN, "domestic-SE")
    assert summary["rail"] == "domestic-SE"
    assert "localInstrument" not in summary


def test_domestic_se_echoes_explicit_instrument():
    summary = _prepare(SE_BBAN, "domestic-SE", local_instrument="INST")
    assert summary["localInstrument"] == "INST"


def test_other_rails_do_not_derive_instruments():
    assert "localInstrument" not in _prepare(SE_IBAN, "sepa")
    assert _prepare(SE_IBAN, "sepa-instant", local_instrument="INST")["localInstrument"] == "INST"


@pytest.mark.parametrize("rail", ["bankgiro", "swish", "domestic-se"])
def test_rail_values_outside_the_enum_are_rejected(rail):
    with pytest.raises((ValidationError, ToolError)):
        _prepare(SE_BBAN, rail)


def test_create_recipient_with_bankgiro_number():
    result = asyncio.run(demo_server.app.call_tool("create-recipient", {
        "name": "Exempel AB",
        "account_identifier": BANKGIRO,
    }))
    item = result.structured_content["item"]
    assert item["accountIdentifier"] == BANKGIRO
