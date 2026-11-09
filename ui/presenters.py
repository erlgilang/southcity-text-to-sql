"""Turns API data into the Indonesian text the interface shows."""

from typing import Any

STEP_LABELS = {
    "load_context": "Menyiapkan konteks",
    "classify": "Memahami pertanyaan",
    "generate_sql": "Menyusun query",
    "validate": "Memeriksa keamanan query",
    "rbac_rewrite": "Menerapkan hak akses",
    "execute": "Mengambil data",
    "retry": "Memperbaiki query",
    "write_answer": "Menulis jawaban",
    "ask_clarification": "Meminta penjelasan",
    "refuse_request": "Menolak permintaan",
    "refuse_unsafe": "Menolak permintaan",
    "give_up": "Berhenti setelah 3 percobaan",
}

INTENT_LABELS = {
    "sql_query": "pertanyaan data",
    "chitchat": "obrolan",
    "clarify": "perlu penjelasan",
    "refuse": "ditolak",
}

ROLE_SCOPE = {
    "Sales": "Anda hanya dapat melihat kontrak milik Anda sendiri dan data unit.",
    "Finance": "Anda dapat melihat seluruh data transaksi.",
    "Auditor": "Anda dapat melihat seluruh data transaksi.",
    "SuperAdmin": "Anda dapat melihat seluruh data transaksi.",
}


def describe_step(step: dict[str, Any]) -> str:
    info = step["info"]
    match step["node"]:
        case "classify":
            return INTENT_LABELS.get(info["intent"], info["intent"])
        case "generate_sql":
            return f"percobaan {info['attempt']}"
        case "validate":
            if info["status"] == "ok":
                return "lolos"
            return f"ditolak, {info['reason']}" if info["retryable"] else "ditolak"
        case "execute":
            if "rows" in info:
                return f"{info['rows']} baris"
            return f"gagal, {info['reason']}"
        case "retry":
            return f"percobaan {info['attempt'] + 1}, karena: {info['error']}"
        case _:
            return ""


def format_seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.1f}".replace(".", ",") + " detik"
