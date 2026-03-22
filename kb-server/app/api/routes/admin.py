from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.models.db import get_session
from app.services import admin_service

router = APIRouter(tags=["admin"])

ADMIN_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>KB Server Admin</title>
  <style>
    :root { --bg:#f5f1e8; --panel:#fffaf0; --ink:#1f2a1f; --muted:#5c665c; --line:#d7ccb7; --accent:#2d6a4f; --warn:#9c4f2d; --bad:#9d2b2b; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background: linear-gradient(180deg, #efe7d8 0%, var(--bg) 60%, #e6efe8 100%); color:var(--ink); }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 24px; }
    .hero { display:flex; justify-content:space-between; gap:16px; align-items:end; margin-bottom:24px; }
    h1,h2,h3 { margin:0 0 8px; }
    p { margin:0; color:var(--muted); }
    .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:16px; margin-bottom:16px; }
    .panel { background:rgba(255,250,240,0.88); border:1px solid var(--line); border-radius:20px; padding:18px; box-shadow:0 10px 30px rgba(61,43,22,0.08); }
    .metrics { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; }
    .metric { border:1px solid var(--line); border-radius:14px; padding:12px; background:#fffdf7; }
    .label { font-size:12px; text-transform:uppercase; letter-spacing:0.08em; color:var(--muted); }
    .value { font-size:24px; font-weight:700; margin-top:6px; }
    .ok { color:var(--accent); }
    .bad { color:var(--bad); }
    .warn { color:var(--warn); }
    form { display:grid; gap:12px; }
    .field { display:grid; gap:6px; }
    .field label { font-weight:600; }
    input { width:100%; border:1px solid var(--line); border-radius:12px; padding:10px 12px; background:#fffef9; }
    button { border:none; border-radius:999px; padding:10px 16px; background:var(--ink); color:white; cursor:pointer; }
    button.secondary { background:#d9cfbd; color:var(--ink); }
    .row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
    .list { margin:0; padding-left:18px; color:var(--muted); }
    .mono { font-family: ui-monospace, SFMono-Regular, monospace; font-size:12px; }
    .status { margin-top:10px; min-height:20px; color:var(--muted); }
    .config-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:12px; }
    .item { border:1px solid var(--line); border-radius:14px; padding:12px; background:#fffdf8; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div>
        <h1>KB Server Admin</h1>
        <p>Setup, config, and runtime visibility for the local KB server instance.</p>
      </div>
      <div class="row">
        <button class="secondary" id="refresh">Refresh</button>
      </div>
    </div>

    <div class="grid">
      <section class="panel">
        <h2>System Status</h2>
        <div class="metrics" id="metrics"></div>
        <div class="status" id="ready-errors"></div>
      </section>
      <section class="panel">
        <h2>Setup Notes</h2>
        <ul class="list">
          <li>Point <span class="mono">VAULT_PATH</span> at an existing local Git repo.</li>
          <li>Process env still overrides <span class="mono">.env</span> values.</li>
          <li>Changing database or auth config usually requires restarting <span class="mono">kb-api</span> and <span class="mono">kb-worker</span>.</li>
        </ul>
      </section>
    </div>

    <div class="grid">
      <section class="panel">
        <h2>Configuration</h2>
        <form id="config-form">
          <div class="config-grid" id="config-fields"></div>
          <div class="row">
            <button type="submit">Save Config</button>
            <span class="status" id="save-status"></span>
          </div>
        </form>
      </section>
      <section class="panel">
        <h2>Vault and Git</h2>
        <div id="vault-git"></div>
      </section>
    </div>

    <div class="grid">
      <section class="panel">
        <h2>Pending PR Workflow</h2>
        <div id="prs"></div>
      </section>
      <section class="panel">
        <h2>Recent Jobs</h2>
        <div id="jobs"></div>
      </section>
    </div>

    <div class="grid">
      <section class="panel">
        <h2>Recent Vault Events</h2>
        <div id="events"></div>
      </section>
      <section class="panel">
        <h2>Publish Runs</h2>
        <div id="publish-runs"></div>
      </section>
    </div>
  </div>

  <script>
    const saveStatus = document.getElementById("save-status");

    function esc(text) {
      return String(text ?? "").replace(/[&<>"]/g, (ch) => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[ch]));
    }

    function renderList(items, formatter) {
      if (!items || items.length === 0) return "<p>No entries yet.</p>";
      return `<ul class="list">${items.map((item) => `<li>${formatter(item)}</li>`).join("")}</ul>`;
    }

    function fieldMarkup(row) {
      const hint = row.secret
        ? `<div class="label">${row.configured ? "Configured" : "Not configured"} via ${esc(row.source)}</div>`
        : `<div class="label">Source: ${esc(row.source)}</div>`;
      const placeholder = row.secret && row.configured ? "set new value to replace" : "";
      const value = row.secret ? "" : row.value;
      return `
        <div class="field item">
          <label for="${esc(row.key)}">${esc(row.key)}</label>
          <input id="${esc(row.key)}" name="${esc(row.key)}" value="${esc(value)}" placeholder="${esc(placeholder)}" ${row.secret ? 'type="password"' : 'type="text"'}>
          ${hint}
        </div>
      `;
    }

    function loadState() {
      fetch("/admin/api/state")
        .then(async (resp) => {
          const contentType = resp.headers.get("content-type") || "";
          if (!resp.ok || !contentType.includes("application/json")) {
            const body = await resp.text();
            throw new Error(body || `request failed (${resp.status})`);
          }
          return resp.json();
        })
        .then((payload) => {
          const state = payload.state;
          document.getElementById("config-fields").innerHTML = payload.config.map(fieldMarkup).join("");
          document.getElementById("metrics").innerHTML = `
            <div class="metric"><div class="label">Readiness</div><div class="value ${state.ready ? "ok" : "bad"}">${state.ready ? "Ready" : "Blocked"}</div></div>
            <div class="metric"><div class="label">Database</div><div class="value ${state.database.status === "ok" ? "ok" : "bad"}">${esc(state.database.status)}</div></div>
            <div class="metric"><div class="label">Pending Batch</div><div class="value">${state.batcher.pending_count}</div></div>
            <div class="metric"><div class="label">Open KB PRs</div><div class="value">${state.prs.count}</div></div>
          `;
          document.getElementById("ready-errors").innerHTML = state.ready_errors.length
            ? renderList(state.ready_errors, (item) => esc(item))
            : "<span class='ok'>All readiness checks passed.</span>";
          document.getElementById("vault-git").innerHTML = `
            <ul class="list">
              <li>Vault path: <span class="mono">${esc(state.vault.path)}</span></li>
              <li>Vault exists: ${state.vault.exists}</li>
              <li>Vault is git repo: ${state.vault.is_git_repo}</li>
              <li>Current branch: <span class="mono">${esc(state.git.branch || state.git.error || "unknown")}</span></li>
              <li>Current SHA: <span class="mono">${esc(state.git.current_sha || "unknown")}</span></li>
              <li>Working tree changes: ${state.git.has_changes ?? "unknown"}</li>
              <li>Queued batch paths: ${state.batcher.pending_paths.length}</li>
            </ul>
          `;
          document.getElementById("prs").innerHTML = state.prs.error
            ? `<p>${esc(state.prs.error)}</p>`
            : renderList(state.prs.items, (item) => `<a href="${esc(item.url)}" target="_blank" rel="noreferrer">#${esc(item.number)} ${esc(item.title)}</a> <span class="mono">${esc(item.head)}</span>`);
          document.getElementById("jobs").innerHTML = renderList(state.jobs, (job) => `${esc(job.type)} <strong>${esc(job.status)}</strong> <span class="mono">#${esc(job.id)}</span>${job.error ? ` - ${esc(job.error)}` : ""}`);
          document.getElementById("events").innerHTML = renderList(state.events, (event) => `${esc(event.type)} <span class="mono">${esc(event.file_path || event.commit_sha || "")}</span>`);
          document.getElementById("publish-runs").innerHTML = renderList(state.publish_runs, (run) => `${esc(run.trigger)} <strong>${esc(run.status)}</strong> <span class="mono">#${esc(run.id)}</span>${run.error ? ` - ${esc(run.error)}` : ""}`);
        })
        .catch((error) => {
          saveStatus.textContent = `Failed to load admin state: ${error}`;
        });
    }

    document.getElementById("config-form").addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(event.target);
      const config = {};
      for (const [key, value] of formData.entries()) {
        config[key] = value;
      }
      saveStatus.textContent = "Saving...";
      fetch("/admin/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config })
      })
        .then(async (resp) => {
          const contentType = resp.headers.get("content-type") || "";
          if (!contentType.includes("application/json")) {
            const body = await resp.text();
            throw new Error(body || `request failed (${resp.status})`);
          }
          return { ok: resp.ok, data: await resp.json() };
        })
        .then(({ ok, data }) => {
          if (!ok) {
            throw new Error(data.detail || "save failed");
          }
          saveStatus.textContent = data.message;
          loadState();
        })
        .catch((error) => {
          saveStatus.textContent = `Save failed: ${error.message}`;
        });
    });

    document.getElementById("refresh").addEventListener("click", loadState);
    loadState();
  </script>
</body>
</html>"""


@router.get("/admin", response_class=HTMLResponse)
def admin_page() -> HTMLResponse:
    return HTMLResponse(ADMIN_HTML)


@router.get("/admin/api/state")
def admin_state(session: Session = Depends(get_session)) -> dict[str, Any]:
    return {
        "config": admin_service.current_config_view(),
        "state": admin_service.system_state(session),
    }


@router.post("/admin/api/config")
async def admin_update_config(request: Request) -> JSONResponse:
    payload = await request.json()
    config = payload.get("config", {})
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="config must be an object")

    allowed = set(admin_service.VISIBLE_CONFIG_KEYS) | set(admin_service.SECRET_CONFIG_KEYS)
    updates: dict[str, str] = {}

    for key, value in config.items():
        if key not in allowed:
            continue
        if key in admin_service.SECRET_CONFIG_KEYS and not value:
            continue
        updates[key] = str(value)

    result = admin_service.update_env_file(updates)
    return JSONResponse(
        {
            "message": "Saved to .env. Restart kb-api and kb-worker to apply auth/database changes reliably.",
            **result,
        }
    )


@router.post("/admin/api/start")
def admin_start() -> JSONResponse:
    runtime = admin_service.runtime_control_state()["api"]
    if not runtime["workdir_exists"]:
        raise HTTPException(status_code=501, detail="ADMIN_TMUX_WORKDIR does not exist")
    if not runtime["venv_python_exists"]:
        raise HTTPException(status_code=501, detail="Configured workdir is missing .venv/bin/python")

    admin_service.launch_command(admin_service.backend_start_command())
    return JSONResponse({"message": "Start command launched"})


@router.post("/admin/api/restart")
def admin_restart() -> JSONResponse:
    runtime = admin_service.runtime_control_state()["api"]
    if not runtime["workdir_exists"]:
        raise HTTPException(status_code=501, detail="ADMIN_TMUX_WORKDIR does not exist")
    if not runtime["venv_python_exists"]:
        raise HTTPException(status_code=501, detail="Configured workdir is missing .venv/bin/python")

    admin_service.launch_command(admin_service.backend_restart_command())
    return JSONResponse({"message": "Restart command launched"})


@router.post("/admin/api/start-worker")
def admin_start_worker() -> JSONResponse:
    runtime = admin_service.runtime_control_state()["worker"]
    if not runtime["workdir_exists"]:
        raise HTTPException(status_code=501, detail="ADMIN_TMUX_WORKDIR does not exist")
    if not runtime["venv_python_exists"]:
        raise HTTPException(status_code=501, detail="Configured workdir is missing .venv/bin/python")

    admin_service.launch_command(admin_service.worker_start_command())
    return JSONResponse({"message": "Worker start command launched"})


@router.post("/admin/api/restart-worker")
def admin_restart_worker() -> JSONResponse:
    runtime = admin_service.runtime_control_state()["worker"]
    if not runtime["workdir_exists"]:
        raise HTTPException(status_code=501, detail="ADMIN_TMUX_WORKDIR does not exist")
    if not runtime["venv_python_exists"]:
        raise HTTPException(status_code=501, detail="Configured workdir is missing .venv/bin/python")

    admin_service.launch_command(admin_service.worker_restart_command())
    return JSONResponse({"message": "Worker restart command launched"})
