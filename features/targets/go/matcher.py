"""AI: Structural matching protocol and helper for Go AST nodes."""

from typing import Protocol, Self, runtime_checkable


@runtime_checkable
class NodeMatchProtocol(Protocol):
    properties: dict
    children: list[Self]


def is_match(src: NodeMatchProtocol, cmp: NodeMatchProtocol) -> bool:
    pass
