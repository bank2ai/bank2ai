"""Transaction categories and the get-categories envelope."""

from pydantic import BaseModel, Field

from .base import _Bank2aiModel


CANONICAL_CATEGORY_IDS: tuple[str, ...] = (
    "Income",
    "Transfer",
    "Groceries",
    "DiningAndEntertainment",
    "Transport",
    "Housing",
    "Utilities",
    "Shopping",
    "Health",
    "Travel",
    "Subscriptions",
    "Fees",
    "Cash",
    "Other",
)
"""Recommended `Category.id` values that all bank2ai servers SHOULD use
when a transaction maps cleanly to one of them. Servers MAY emit
additional, server-specific ids when nothing in the canonical list fits.
Clients MUST treat any `Category.id` as opaque (canonical ids are not
the only valid values)."""


class Category(_Bank2aiModel):
    """Transaction category for spending classification.

    bank2ai-defined categorization model; not profiled from a single
    upstream standard. Localized names live on this object so clients
    can render category labels per the user's locale; programmatic
    identity goes through `id`. See `CANONICAL_CATEGORY_IDS` for the
    recommended id values shared across servers.
    """

    id: str = Field(
        description=(
            "Unique category identifier. SHOULD be one of the canonical ids "
            "in `CANONICAL_CATEGORY_IDS` when a server's category maps "
            "cleanly; otherwise free-form server-specific."
        ),
        examples=["Groceries", "DiningAndEntertainment", "Other"],
    )
    name: str = Field(
        description="Category name (localized)",
        examples=["Groceries", "Transportation", "Entertainment", "Utilities"],
    )


class CategoryList(BaseModel):
    """Envelope for a list of categories"""

    items: list[Category] = Field(description="Available transaction categories.")
