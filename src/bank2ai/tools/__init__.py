"""Reusable bank2ai MCP tool specification.

This package isolates the bank2ai tool spec, names, descriptions, input
parameter signatures, and Pydantic response models, so multiple MCP
servers can expose the same surface without duplicating it. Each server
provides async handler callables and calls `register_tools(app, ...)`.

By default, output schemas are inferred by FastMCP from the Pydantic
response-model annotations on the registered tool functions. Servers
can opt into progressive disclosure (lean `list_tools` payloads, full
output schemas fetched on demand via a `describe-tools` meta tool) by
passing ``output_schemas="discovery"`` to ``register_tools``.

Tool registrations are split by domain across the submodules of this
package; `register_tools` is the supported entry point.
"""

from .base import Handler, OutputSchemaMode
from .register import register_tools

__all__ = [
    "Handler",
    "OutputSchemaMode",
    "register_tools",
]
