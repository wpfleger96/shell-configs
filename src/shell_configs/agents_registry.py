"""Deprecated agent registry — retired agents to clean up if found."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class DeprecatedAgentSpec:
    """A retired agent that should be removed if found installed."""

    agent_id: str
    command_name: str
    is_still_in_use: Callable[[], bool] | None = None


DEPRECATED_AGENTS: tuple[DeprecatedAgentSpec, ...] = ()
