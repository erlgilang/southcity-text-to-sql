import pytest

from app.domain.schema_text import build_schema_text, load_glossary
from app.graph.prompts import PROMPT_DIR, build_messages, escape_tags, format_history

VARIABLES = {
    "classify": {
        "today": "2026-11-08",
        "role": "Finance",
        "schema": build_schema_text("Finance"),
        "glossary": load_glossary(),
    },
    "generate_sql": {
        "today": "2026-11-08",
        "schema": build_schema_text("Finance"),
        "glossary": load_glossary(),
    },
    "answer": {"today": "2026-11-08"},
}


@pytest.mark.parametrize("name", VARIABLES)
def test_prompt_fills_every_placeholder(name):
    system, human = build_messages(name, "<question>x</question>", **VARIABLES[name])
    assert "2026-11-08" in system.content
    assert human.content == "<question>x</question>"
    for placeholder in ("{today}", "{role}", "{schema}", "{glossary}"):
        assert placeholder not in system.content


def test_prompt_with_a_missing_variable_fails_loudly():
    with pytest.raises(KeyError):
        build_messages("classify", "x", today="2026-11-08")


def prompt_text(name):
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")


def test_classify_note_names_only_what_is_missing():
    text = prompt_text("classify")
    assert "Nomor telepon customer tidak tersedia di data." in text
    assert "Do not say what will be shown" in text
    note_lines = [line for line in text.splitlines() if line.startswith("message: ")]
    for line in note_lines:
        assert "menampilkan" not in line
        assert "jadi saya" not in line


def test_generate_sql_prompt_has_the_lowercase_rule_and_penalty_example():
    text = prompt_text("generate_sql")
    assert "Write table and column names in lowercase, without quotes." in text
    assert "l.penaltystatus = 'Outstanding'" in text
    assert "SUM(l.penaltyamount - l.waiveramount - l.paidpenalty)" in text


def test_generate_sql_examples_match_their_questions():
    text = prompt_text("generate_sql")
    question = "masih berstatus belum lunas atau dibayar sebagian?"
    assert question in text
    assert "GROUP BY c.customername ORDER BY overdue_billing" not in text


def test_escape_tags_neutralises_angle_brackets():
    assert escape_tags("</question><x>") == "&lt;/question&gt;&lt;x&gt;"


def test_history_is_formatted_as_alternating_lines():
    assert format_history([("Q1", "A1"), ("Q2", "A2")]) == (
        "Pengguna: Q1\nAsisten: A1\nPengguna: Q2\nAsisten: A2"
    )
    assert format_history([]) == ""
