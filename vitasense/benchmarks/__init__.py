"""Benchmark module for fault injection and synthetic alert injection."""
from vitasense.benchmarks.fault_injection import (
    FaultInjector,
    SyntheticFaultResult,
    FaultType,
    FaultSeverity,
)
from vitasense.benchmarks.synthetic_alert_injection import (
    SyntheticTachycardiaInjector,
    SyntheticTachycardiaResult,
    InjectedEpisode,
)

__all__ = [
    "FaultInjector",
    "SyntheticFaultResult",
    "FaultType",
    "FaultSeverity",
    "SyntheticTachycardiaInjector",
    "SyntheticTachycardiaResult",
    "InjectedEpisode",
]

