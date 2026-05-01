"""Bank adapter package."""

import importlib
import logging
import os

from dotenv import load_dotenv

from adapters.base import BankAdapter


def get_adapter(logger: logging.Logger) -> BankAdapter:
    """Load the configured bank adapter.

    Reads BANK2AI_ADAPTER env var. The value is the folder name under adapters/
    that contains the adapter implementation. Each adapter folder must have an
    __init__.py that exports a class inheriting from BankAdapter.

    Example: BANK2AI_ADAPTER=demo loads adapters.demo.DemoDataAdapter
    """
    load_dotenv()

    adapter_name = os.getenv("BANK2AI_ADAPTER", "demo")
    logger.info("Loading adapter: %s", adapter_name)
    module = importlib.import_module(f"adapters.{adapter_name}")

    # Find the BankAdapter subclass exported by the module
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, BankAdapter)
            and attr is not BankAdapter
        ):
            logger.info("Found adapter class: %s", attr.__name__)
            return attr(logger=logger)

    raise ValueError(
        f"No BankAdapter subclass found in adapters.{adapter_name}. "
        f"Ensure the adapter's __init__.py exports a BankAdapter implementation."
    )
