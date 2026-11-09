from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

POLICY_FILE = Path(__file__).with_name("rbac_policy.yaml")


@dataclass(frozen=True)
class RolePolicy:
    tables: frozenset[str]
    hidden_columns: frozenset[str]
    agent_scoped: bool


@dataclass(frozen=True)
class Policy:
    columns: dict[str, list[str]]
    blocked_tables: frozenset[str]
    agent_direct: dict[str, str]
    agent_via_contract: frozenset[str]
    roles: dict[str, RolePolicy]

    def for_role(self, role: str) -> RolePolicy:
        try:
            return self.roles[role]
        except KeyError:
            raise ValueError(f"Unknown role: {role}") from None


@cache
def load_policy() -> Policy:
    raw = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    roles = {
        name: RolePolicy(
            tables=frozenset(role["tables"]),
            hidden_columns=frozenset(role["hidden_columns"]),
            agent_scoped=role["agent_scoped"],
        )
        for name, role in raw["roles"].items()
    }
    return Policy(
        columns=raw["tables"],
        blocked_tables=frozenset(raw["blocked_tables"]),
        agent_direct=raw["agent_scope"]["direct"],
        agent_via_contract=frozenset(raw["agent_scope"]["via_contract"]),
        roles=roles,
    )
