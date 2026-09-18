"""AI: Enumeration of pattern-matching modes (match-one vs. match-all)."""

from enum import StrEnum


class PatternKind(StrEnum):
    MATCH_ONE = "match_one"
    MATCH_ALL = "match_all"
