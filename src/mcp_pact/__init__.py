"""Consumer-driven contract testing for MCP servers."""

from .compat import CompatibilityReport, classify_schema_change, is_type_compatible
from .consumer import ConsumerContract, Interaction, load_consumer_contract
from .fuzz import FuzzCase, generate_fuzz_cases
from .provider import ProviderSurface, ToolSurface, load_provider_surface
from .verify import VerificationResult, can_i_deploy, verify_consumer_against_provider

__all__ = [
    "CompatibilityReport",
    "ConsumerContract",
    "FuzzCase",
    "Interaction",
    "ProviderSurface",
    "ToolSurface",
    "VerificationResult",
    "can_i_deploy",
    "classify_schema_change",
    "generate_fuzz_cases",
    "is_type_compatible",
    "load_consumer_contract",
    "load_provider_surface",
    "verify_consumer_against_provider",
]

__version__ = "0.1.0"
