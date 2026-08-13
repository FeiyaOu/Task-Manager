"""Task lifecycle states (feature 04).

v1 only sets PENDING / UNASSIGNED; ACCEPTED / DECLINED are wired now so the
accept/decline extension is a state transition, not a schema migration.
"""
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    UNASSIGNED = "unassigned"
