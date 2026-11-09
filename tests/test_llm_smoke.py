import pytest

from app.llm.models import get_llm

pytestmark = pytest.mark.llm


def test_default_model_answers():
    reply = get_llm().invoke("What is 2 + 2? Answer with the digit only.")
    assert "4" in reply.text
