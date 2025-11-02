"""Backward compatibility shim for src.reporting imports.

This module maintains backward compatibility by importing BacktestReporter
from the new reporting package structure.
"""

from reporting import BacktestReporter

__all__ = ['BacktestReporter']
