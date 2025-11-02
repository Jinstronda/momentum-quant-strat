"""Backward compatibility shim - redirects to new stormguard package.

The StormGuard filter has been refactored into a modular package structure:
- src/stormguard/metrics.py: All 5 metric calculation functions
- src/stormguard/state_machine.py: Bull/Bear state logic
- src/stormguard/calculator.py: Main orchestrator

This file maintains backward compatibility for existing imports.
"""

from src.stormguard.calculator import StormGuardCalculator

__all__ = ['StormGuardCalculator']
