# vault-sync

Daemon that keeps a local directory in sync with the kb-server **current** view (approved content from `main` plus pending agent changes from open PRs). Edit files locally and they are pushed to the server automatically.

## How it works

1. On startup, pulls every note from the server's `current` view into a local directory.
2. Watches that directory for file changes (create, edit, delete).
3. When you save a file, it pushes the change to the kb-server API with `source=human`, which commits directly to `main`.
4. Periodically re-pulls from the server to pick up new agent-written content or merged PRs.

Supported file types: `.md`, `.markdown`, `.txt`.

## Prerequisites

- Python 3.10 or later
- A running kb-server instance with an API key configured
- Network access from your machine to the kb-server

## Setup

### 1. Clone the repo

```bash
git clone <your-repo-url> flight-deck
cd flight-deck/vault-sync
```

### 2. Create a virtual environment

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install

```bash
pip install .
```

For development (includes test dependencies):

```bash
pip install -e ".[dev]"
```

### 4. Configure

Create a `.env` file in the `vault-sync/` directory (or export the variables directly):

```bash
cat > .env << 'EOF'
KB_SERVER_URL=http://your-server:8000
KB_API_KEY=your-api-key-here
SYNC_DIR=~/vault-sync-data
EOF
```

| Variable | Description | Default |
|----------|-------------|---------|
| `KB_SERVER_URL` | URL of the kb-server | `http://localhost:8000` |
| `KB_API_KEY` | API key for authentication | *(empty -- required)* |
| `SYNC_DIR` | Local directory to sync files into | `~/vault-sync` |
| `SYNC_DEBOUNCE_SECONDS` | Wait time before pushing local edits | `2` |
| `SYNC_PULL_INTERVAL_SECONDS` | How often to refresh from the server | `30` |

### 5. Run

```bash
vault-sync
```

Or with explicit options:

```bash
vault-sync --server http://my-server:8000 --dir ~/my-vault --interval 60 -v
```

The daemon runs in the foreground. Press `Ctrl+C` to stop.

## CLI options

```
Usage: vault-sync [OPTIONS]

  Sync a local directory with the kb-server current view.

Options:
  --dir PATH        Local directory to sync (default: ~/vault-sync or SYNC_DIR env).
  --server TEXT     KB server URL (default: http://localhost:8000 or KB_SERVER_URL env).
  --interval FLOAT  Pull interval in seconds (default: 30).
  --debounce FLOAT  Debounce interval in seconds (default: 2).
  -v, --verbose     Enable debug logging.
  --help            Show this message and exit.
```

## Running as a background service

### systemd (Linux)

Create `~/.config/systemd/user/vault-sync.service`:

```ini
[Unit]
Description=Vault Sync Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/flight-deck/vault-sync
ExecStart=%h/flight-deck/vault-sync/.venv/bin/vault-sync
Restart=on-failure
RestartSec=10
EnvironmentFile=%h/flight-deck/vault-sync/.env

[Install]
WantedBy=default.target
```

Then:

```bash
systemctl --user daemon-reload
systemctl --user enable vault-sync
systemctl --user start vault-sync

# Check status
systemctl --user status vault-sync

# View logs
journalctl --user -u vault-sync -f
```

### launchd (macOS)

Create `~/Library/LaunchAgents/com.flightdeck.vault-sync.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.flightdeck.vault-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOU/flight-deck/vault-sync/.venv/bin/vault-sync</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOU/flight-deck/vault-sync</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>KB_SERVER_URL</key>
        <string>http://your-server:8000</string>
        <key>KB_API_KEY</key>
        <string>your-api-key-here</string>
        <key>SYNC_DIR</key>
        <string>/Users/YOU/vault-sync-data</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/vault-sync.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/vault-sync.err</string>
</dict>
</plist>
```

Replace `/Users/YOU` with your actual home directory, then:

```bash
launchctl load ~/Library/LaunchAgents/com.flightdeck.vault-sync.plist

# Check status
launchctl list | grep vault-sync

# View logs
tail -f /tmp/vault-sync.log

# Stop
launchctl unload ~/Library/LaunchAgents/com.flightdeck.vault-sync.plist
```

## Running tests

```bash
pip install -e ".[dev]"
python3 -m pytest -v
```

## Troubleshooting

**"Connection refused" on startup** -- The kb-server is not reachable. Check `KB_SERVER_URL` and make sure the server is running.

**"401 Unauthorized"** -- `KB_API_KEY` is missing or does not match the server's configured key.

**Files not appearing locally** -- Run with `-v` to see debug output. Check that the server has notes (try `curl -H "X-API-Key: $KB_API_KEY" $KB_SERVER_URL/notes/?view=current`).

**Edits not pushing** -- The daemon debounces changes (default 2s). Wait a moment and check the logs. Verify the server accepts writes (`PUT /notes/{path}?source=human`).
