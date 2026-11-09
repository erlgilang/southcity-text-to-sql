import streamlit as st
from api_client import ApiClient, ApiError, SessionExpiredError
from presenters import ROLE_SCOPE, STEP_LABELS, describe_step, format_seconds
from pydantic_settings import BaseSettings, SettingsConfigDict

EXAMPLE_QUESTIONS = [
    "Unit apa saja yang masih kosong di Tower B, beserta tipe dan lantainya?",
    "Siapa saja customer yang masih punya denda keterlambatan belum lunas?",
]
LOADING_TEXT = (
    "Memahami pertanyaan, menyusun query, dan mengambil data. Biasanya 5 sampai 10 detik."
)


class UiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_base_url: str


@st.cache_resource
def get_client() -> ApiClient:
    return ApiClient(UiSettings().api_base_url)


@st.cache_data(ttl=300, show_spinner=False)
def get_users() -> list[dict]:
    return get_client().list_users()


def start_session(username: str) -> None:
    st.session_state.session = get_client().create_session(username)
    st.session_state.messages = []


def render_table(table: dict) -> None:
    columns = table["columns"]
    money = set(table["money_columns"])
    st.dataframe(
        {name: [row[i] for row in table["rows"]] for i, name in enumerate(columns)},
        column_config={
            name: st.column_config.TextColumn(name, alignment="right")
            for name in columns
            if name in money
        },
        hide_index=True,
    )
    if table["truncated"]:
        st.caption("Tabel dipotong pada 200 baris. Persempit pertanyaan untuk melihat sisanya.")


def render_assistant(message: dict) -> None:
    st.markdown(message["content"])
    if message.get("table") and message["table"]["rows"]:
        render_table(message["table"])
    if message.get("steps"):
        with st.expander("Proses"):
            st.dataframe(
                {
                    "Langkah": [STEP_LABELS[s["node"]] for s in message["steps"]],
                    "Waktu": [format_seconds(s["ms"]) for s in message["steps"]],
                    "Keterangan": [describe_step(s) for s in message["steps"]],
                },
                hide_index=True,
            )
            st.caption(f"Total waktu {format_seconds(message['total_ms'])}")
    if message.get("sql"):
        with st.expander("SQL"):
            st.code(message["sql"], language="sql")


def ask(question: str) -> None:
    client = get_client()
    with st.chat_message("user"):
        st.markdown(question)
    messages = st.session_state.messages
    messages.append({"role": "user", "content": question})
    with st.chat_message("assistant"):
        try:
            with st.spinner(LOADING_TEXT):
                try:
                    reply = client.chat(st.session_state.session["session_id"], question)
                except SessionExpiredError:
                    # The server forgot the session (restart). Keep the user, drop the history.
                    start_session(st.session_state.username)
                    messages = st.session_state.messages
                    messages.append({"role": "user", "content": question})
                    st.session_state.notice = (
                        "Sesi sebelumnya berakhir di server, "
                        "jadi riwayat percakapan dimulai dari awal."
                    )
                    reply = client.chat(st.session_state.session["session_id"], question)
        except ApiError as error:
            message = {"role": "assistant", "content": str(error)}
            st.error(str(error))
        else:
            message = {
                "role": "assistant",
                "content": reply["answer"],
                "table": reply["table"],
                "steps": reply["steps"],
                "sql": reply["sql"],
                "total_ms": reply["total_ms"],
            }
            render_assistant(message)
    messages.append(message)


st.set_page_config(page_title="Asisten Data Properti", layout="wide")

try:
    users = get_users()
except ApiError as error:
    st.error(str(error))
    st.stop()

by_username = {user["username"]: user for user in users}

with st.sidebar:
    st.header("Asisten Data Properti")
    username = st.selectbox(
        "Pilih user",
        list(by_username),
        format_func=lambda name: f"{name} ({by_username[name]['role']})",
    )
    st.caption("Mengganti user memulai percakapan baru dengan riwayat kosong.")

if st.session_state.get("username") != username:
    try:
        start_session(username)
    except ApiError as error:
        st.error(str(error))
        st.stop()
    st.session_state.username = username
    st.session_state.notice = ""

user = by_username[username]
st.markdown(f"Sedang masuk sebagai **{user['full_name']}**, role **{user['role']}**.")
st.caption(ROLE_SCOPE.get(user["role"], ""))
if st.session_state.notice:
    st.info(st.session_state.notice)

pending = st.session_state.pop("pending_question", None)

if not st.session_state.messages and not pending:
    st.write("Tanyakan data unit, kontrak, tagihan, pembayaran, atau denda. Contoh:")
    for index, example in enumerate(EXAMPLE_QUESTIONS):
        if st.button(example, key=f"example_{index}"):
            st.session_state.pending_question = example
            st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            render_assistant(message)

question = st.chat_input(
    "Tulis pertanyaan tentang unit, kontrak, tagihan, atau denda", max_chars=500
)
if question or pending:
    ask(question or pending)
