"""Collects the request_summary lines of the live tests for the report at the end of a run."""

from collections import defaultdict

RECORDS: list[tuple[str, dict]] = []  # (kind of question, request_summary fields)


def summary_lines() -> list[str]:
    groups = defaultdict(list)
    for kind, summary in RECORDS:
        groups[kind].append(summary)
    lines = []
    for kind, items in sorted(groups.items()):
        count = len(items)

        def average(field, items=items, count=count):
            return sum(item[field] for item in items) / count

        lines.append(
            f"{kind:<22} n={count:<3} total={average('total_ms') / 1000:5.1f}s "
            f"llm={average('llm_ms') / 1000:5.1f}s db={average('db_ms') / 1000:4.1f}s "
            f"llm_calls={average('llm_calls'):.1f} sql_attempts={average('sql_attempts'):.1f} "
            f"tokens_in={average('input_tokens'):.0f} tokens_out={average('output_tokens'):.0f}"
        )
    return lines
