"""Transfer rails, validation, and the prepare/execute envelopes."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .accounts import Account
from .base import _Bank2aiModel
from .identity import Party
from .transactions import RemittanceInformation


class TransferAction(BaseModel):
    """Suggested follow-up action for a prepared transfer."""

    title: str = Field(description="Human-readable label for the action.")
    link: str = Field(description="Target URL or in-app link to perform the action.")


class Rail(str, Enum):
    """Payment rail used to settle a transfer.

    Servers MAY register additional rails via vendor extensions; the
    canonical list reflects the rails the reference implementations
    exercise today.
    """

    DomesticIS = "domestic-IS"
    SEPA = "sepa"
    SEPAInstant = "sepa-instant"
    SWIFT = "swift"


class TransferFee(_Bank2aiModel):
    """One fee line item that will apply to the transfer."""

    amount: float = Field(description="Fee amount in `currency`.")
    currency: str = Field(
        description="ISO 4217 currency code.",
        pattern="^[A-Z]{3}$",
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable label for the fee.",
        examples=["Wire fee", "FX margin"],
    )


class TransferFx(_Bank2aiModel):
    """Foreign-exchange details for a cross-currency transfer."""

    rate: float = Field(description="Exchange rate applied (sourceAmount * rate = targetAmount).")
    sourceAmount: float = Field(description="Amount debited from the debtor account.")
    sourceCurrency: str = Field(
        description="Currency of the debtor account.",
        pattern="^[A-Z]{3}$",
    )
    targetAmount: float = Field(description="Amount credited to the creditor.")
    targetCurrency: str = Field(
        description="Currency the creditor receives.",
        pattern="^[A-Z]{3}$",
    )
    lockedUntil: Optional[datetime] = Field(
        default=None,
        description="ISO 8601 timestamp until which the quoted rate is held.",
    )


class ConfirmationOfPayeeStatus(str, Enum):
    """Outcome of a payee verification check (UK CoP, EU VoP, etc.)."""

    Match = "match"
    CloseMatch = "close-match"
    NoMatch = "no-match"
    Unavailable = "unavailable"


class ConfirmationOfPayee(_Bank2aiModel):
    """Result of a payee-name verification against the destination account."""

    status: ConfirmationOfPayeeStatus = Field(description="Verification outcome.")
    suggestedName: Optional[str] = Field(
        default=None,
        description=(
            "On a `close-match` or `no-match`, the actual name on the "
            "destination account when the rail returns it."
        ),
    )


class TransferWarningSeverity(str, Enum):
    """How a client should treat a transfer warning."""

    Info = "info"
    Warn = "warn"
    Block = "block"


class TransferWarning(_Bank2aiModel):
    """Server-emitted advisory about a prepared transfer.

    Used for AML hits, sanctions matches, unusual-amount notices, etc.
    `severity: "block"` indicates the server will refuse `execute-transfer`
    against this intent unless the user explicitly overrides.
    """

    code: str = Field(description="Server-defined warning code.")
    message: str = Field(description="Human-readable explanation.")
    severity: TransferWarningSeverity = Field(description="Warning severity.")


class TransferSummary(_Bank2aiModel):
    """Validated, normalized echo of the prepare-transfer inputs.

    The user-facing confirmation surface: clients should render this
    so the user can confirm before `execute-transfer` is called.
    """

    debtorAccount: Account = Field(
        description="Resolved snapshot of the debtor (source) account.",
    )
    creditor: Party = Field(
        description=(
            "Validated creditor record. The `accountIdentifier` field "
            "carries the routing identifier; servers MUST populate it."
        ),
    )
    amount: float = Field(description="Transfer amount in `currency`.", gt=0)
    currency: str = Field(
        description="ISO 4217 currency code of the instructed amount.",
        pattern="^[A-Z]{3}$",
        examples=["ISK", "EUR", "USD"],
    )
    rail: Rail = Field(description="Settlement rail.")
    localInstrument: Optional[str] = Field(
        default=None,
        description=(
            "Rail-specific local instrument code (e.g., `INST` for SEPA "
            "Instant)."
        ),
    )
    requestedExecutionDate: Optional[date] = Field(
        default=None,
        description=(
            "Requested execution date, ISO 8601. Omitted means "
            "as-soon-as-possible per the rail's defaults."
        ),
    )
    remittanceInformation: Optional[RemittanceInformation] = Field(
        default=None,
        description="Remittance information, when present.",
    )
    endToEndId: str = Field(
        description=(
            "ISO 20022 cross-rail identifier. Server-generated when the "
            "client did not supply one; populated either way so the "
            "client can show / audit the value."
        ),
    )
    description: Optional[str] = Field(
        default=None,
        description=(
            "Free-text shown on the counterparty's statement. Falls "
            "back to `remittanceInformation.unstructured` when both are "
            "present."
        ),
    )


class PreparedTransfer(_Bank2aiModel):
    """Result of a successful `prepare-transfer` call.

    `transferIntentId` is the opaque token the client passes to
    `execute-transfer`. `summary` is what the user confirms; everything
    else is supporting metadata (fees, FX, payee verification, warnings).
    """

    transferIntentId: str = Field(
        description="Opaque intent token; pass to `execute-transfer`.",
    )
    expiresAt: datetime = Field(
        description=(
            "ISO 8601 timestamp after which `execute-transfer` will "
            "reject the intent. Servers SHOULD set this 5 minutes ahead "
            "of the prepare time; rails MAY shorten or extend."
        ),
    )
    fees: Optional[list[TransferFee]] = Field(
        default=None,
        description="Fees the bank will charge for this transfer.",
    )
    fx: Optional[TransferFx] = Field(
        default=None,
        description="FX details when the transfer crosses currencies.",
    )
    estimatedSettlement: Optional[datetime] = Field(
        default=None,
        description="ISO 8601 estimated settlement time at the creditor.",
    )
    confirmationOfPayee: Optional[ConfirmationOfPayee] = Field(
        default=None,
        description=(
            "Payee verification outcome. Servers on rails that support "
            "Confirmation of Payee / Verification of Payee MUST populate "
            "this when known. Servers on rails that do not SHOULD omit."
        ),
    )
    warnings: Optional[list[TransferWarning]] = Field(
        default=None,
        description="Advisory or blocking warnings emitted during validation.",
    )
    summary: TransferSummary = Field(
        description=(
            "Validated echo of the prepare-transfer inputs; the "
            "user-facing confirmation surface."
        ),
    )


class PrepareTransferResponse(BaseModel):
    """Envelope for `prepare-transfer`. Recoverable-error pattern: when
    validation succeeded `item` is populated; when it failed `content`
    explains why and `item` is omitted."""

    content: str = Field(description="Human-readable status message.")
    item: Optional[PreparedTransfer] = Field(
        default=None,
        description="Prepared transfer details when validation succeeded.",
    )
    actions: list[TransferAction] = Field(
        default_factory=list,
        description="Optional follow-up actions the client may surface.",
    )
    code: Optional[str] = Field(
        default=None,
        description=(
            "Server-defined code identifying a recoverable error (e.g., "
            "`insufficient_funds`, `invalid_account`, `missing_creditor_identifier`). "
            "Omitted on success."
        ),
    )


class TransferExecutionStatus(str, Enum):
    """Reported execution outcome for `execute-transfer`."""

    Accepted = "Accepted"
    Pending = "Pending"
    Settled = "Settled"
    Rejected = "Rejected"


class ExecutedTransfer(_Bank2aiModel):
    """Bank-issued receipt for an executed transfer."""

    transactionId: str = Field(
        description=(
            "`Transaction.id` of the resulting bank transaction. Use "
            "with `get-transaction` to fetch full details."
        ),
    )
    status: TransferExecutionStatus = Field(
        description="Execution status reported by the bank.",
    )
    rejectionReason: Optional[str] = Field(
        default=None,
        description="Human-readable reason when `status` is `Rejected`.",
    )
    executedAt: datetime = Field(
        description="ISO 8601 timestamp when the bank recorded the transfer.",
    )


class ExecuteTransferResponse(BaseModel):
    """Envelope for `execute-transfer`."""

    content: str = Field(description="Human-readable status message.")
    item: Optional[ExecutedTransfer] = Field(
        default=None,
        description="Receipt details when the transfer was accepted by the bank.",
    )
    code: Optional[str] = Field(
        default=None,
        description=(
            "Server-defined code identifying a recoverable error. "
            "Canonical values: `intent_expired`, `intent_not_found`. "
            "Omitted on success."
        ),
    )
