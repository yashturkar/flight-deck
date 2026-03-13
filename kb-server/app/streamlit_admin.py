from __future__ import annotations

import httpx
import streamlit as st

from app.core.config import settings
from app.services import admin_service


def backend_url() -> str:
    return st.session_state.get("backend_url", "http://localhost:8000").rstrip("/")


def api_request(method: str, path: str, *, json: dict | None = None) -> httpx.Response:
    with httpx.Client(timeout=10) as client:
        return client.request(method, f"{backend_url()}{path}", json=json)


def try_api_request(method: str, path: str, *, json: dict | None = None) -> tuple[httpx.Response | None, str | None]:
    try:
        return api_request(method, path, json=json), None
    except httpx.HTTPError as exc:
        return None, str(exc)


def run_local_command(command: str, missing_message: str) -> None:
    if not command:
        st.error(missing_message)
        return
    admin_service.launch_command(command)
    st.success("Command launched")


def format_value(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "-"
    if value == "":
        return "-"
    return str(value)


def render_kv(title: str, values: dict) -> None:
    st.subheader(title)
    rows = [{"Field": key.replace("_", " ").title(), "Value": format_value(value)} for key, value in values.items()]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_table(title: str, rows: list[dict], *, empty_message: str) -> None:
    st.subheader(title)
    if not rows:
        st.caption(empty_message)
        return
    formatted_rows = []
    for row in rows:
        formatted_rows.append(
            {key.replace("_", " ").title(): format_value(value) for key, value in row.items()}
        )
    st.dataframe(formatted_rows, use_container_width=True, hide_index=True)


st.set_page_config(page_title="KB Server Dashboard", layout="wide")
st.title("KB Server Dashboard")

st.sidebar.text_input("Backend URL", value="http://localhost:8000", key="backend_url")

with st.sidebar:
    st.subheader("Server Control")
    if st.button("Start kb-server"):
        run_local_command(
            settings.admin_start_command,
            "ADMIN_START_COMMAND is not configured in .env",
        )
    if st.button("Restart kb-server"):
        run_local_command(
            settings.admin_restart_command,
            "ADMIN_RESTART_COMMAND is not configured in .env",
        )
    if settings.admin_start_command:
        st.caption(f"Start: `{settings.admin_start_command}`")
    if settings.admin_restart_command:
        st.caption(f"Restart: `{settings.admin_restart_command}`")

state_response, state_error = try_api_request("GET", "/admin/api/state")
if state_response is None:
    st.warning(f"Backend offline: {state_error}")
    st.info("Use the sidebar controls to start the server, then click Rerun in Streamlit.")
    st.stop()

if not state_response.is_success:
    st.error(state_response.text)
    st.stop()

payload = state_response.json()
state = payload["state"]
config_rows = payload["config"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ready", "yes" if state["ready"] else "no")
col2.metric("DB", state["database"]["status"])
col3.metric("Pending Batch", state["batcher"]["pending_count"])
col4.metric("Open KB PRs", state["prs"]["count"])

if state["ready_errors"]:
    st.warning("\n".join(state["ready_errors"]))

st.subheader("Configuration")
with st.form("config"):
    updates: dict[str, str] = {}
    left, right = st.columns(2)
    for idx, row in enumerate(config_rows):
        target = left if idx % 2 == 0 else right
        label = f"{row['key']}"
        help_text = f"Source: {row['source']}"
        with target:
            if row["secret"]:
                updates[row["key"]] = st.text_input(label, type="password", help=help_text)
            else:
                updates[row["key"]] = st.text_input(
                    label,
                    value=row["value"],
                    help=help_text,
                )
    if st.form_submit_button("Save Config"):
        save_response, save_error = try_api_request("POST", "/admin/api/config", json={"config": updates})
        if save_response is None:
            st.error(save_error)
            st.stop()
        if save_response.is_success:
            st.success(save_response.json()["message"])
        else:
            st.error(save_response.text)

info_left, info_right = st.columns(2)
with info_left:
    render_kv("Vault", state["vault"])
with info_right:
    render_kv("Git", state["git"])

ops_left, ops_right = st.columns(2)
with ops_left:
    render_kv("Database", state["database"])
with ops_right:
    render_kv("Batcher", state["batcher"])

with st.expander("Pending PRs", expanded=True):
    render_table(
        "Open Pull Requests",
        state["prs"].get("items", []),
        empty_message=state["prs"].get("error", "No open kb-api PRs."),
    )

with st.expander("Recent Jobs", expanded=True):
    render_table("Job Activity", state["jobs"], empty_message="No jobs yet.")

with st.expander("Recent Events", expanded=False):
    render_table("Vault Events", state["events"], empty_message="No events yet.")

with st.expander("Publish Runs", expanded=False):
    render_table("Publish History", state["publish_runs"], empty_message="No publish runs yet.")
