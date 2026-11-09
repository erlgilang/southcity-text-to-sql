from sqlglot import exp

from app.domain.policy import Policy, RolePolicy, load_policy


def apply_rbac(statement: exp.Query, role: str, agent_id: int | None) -> exp.Query:
    """Return a copy where every restricted table is a subquery with only allowed rows and columns.

    Expects a statement that already passed validate_sql. The agent id must come from the
    server session, never from the question.
    """
    policy = load_policy()
    role_policy = policy.for_role(role)
    if role_policy.agent_scoped and agent_id is None:
        raise ValueError(f"Role {role} is limited to one sales agent, so agent_id is required")

    tree = statement.copy()
    cte_names = {cte.alias.lower() for cte in tree.find_all(exp.CTE)}
    # Collect first: replacing nodes while walking the tree would skip or revisit tables
    tables = [
        table
        for table in tree.find_all(exp.Table)
        if isinstance(table.this, exp.Identifier) and table.name.lower() not in cte_names
    ]
    for table in tables:
        restricted = _restricted_source(table, policy, role_policy, agent_id)
        if restricted is not None:
            table.replace(restricted)
    return tree


def _restricted_source(
    table: exp.Table, policy: Policy, role_policy: RolePolicy, agent_id: int | None
) -> exp.Subquery | None:
    name = table.name.lower()
    if name not in policy.columns:
        raise ValueError(f"Table {name} is not covered by the RBAC policy")

    columns = [c for c in policy.columns[name] if c not in role_policy.hidden_columns]
    condition = _agent_condition(name, policy, agent_id) if role_policy.agent_scoped else None
    if condition is None and len(columns) == len(policy.columns[name]):
        return None

    query = exp.select(*(exp.column(column) for column in columns)).from_(exp.to_table(name))
    if condition is not None:
        query = query.where(condition)
    # Keep the original alias so references like c.customername still resolve
    return query.subquery(alias=table.alias_or_name)


def _agent_condition(table: str, policy: Policy, agent_id: int) -> exp.Expression | None:
    agent = exp.Literal.number(int(agent_id))
    if table in policy.agent_direct:
        return exp.column(policy.agent_direct[table]).eq(agent)
    if table in policy.agent_via_contract:
        owned_contracts = (
            exp.select(exp.column("contractid"))
            .from_(exp.to_table("sales_contracts"))
            .where(exp.column(policy.agent_direct["sales_contracts"]).eq(agent))
        )
        return exp.column("contractid").isin(query=owned_contracts)
    return None
