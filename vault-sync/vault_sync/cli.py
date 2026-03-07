"""Entry point for the vault-sync daemon."""

from __future__ import annotations

import logging
import signal
import sys
import time
from pathlib import Path

import click

from vault_sync.api_client import KBClient
from vault_sync.config import Settings
from vault_sync.sync import pull_current, push_changes
from vault_sync.watcher import EchoGuard, SyncWatcher

log = logging.getLogger(__name__)


def _run_loop(
    sync_dir: Path,
    client: KBClient,
    debounce: float,
    pull_interval: float,
) -> None:
    echo_guard = EchoGuard()
    watcher = SyncWatcher(sync_dir, echo_guard)

    stop = False

    def _handle_signal(signum: int, frame: object) -> None:
        nonlocal stop
        log.info("received signal %d, shutting down", signum)
        stop = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    log.info("initial pull from server")
    touched = pull_current(sync_dir, client)
    echo_guard.mark(touched)

    watcher.start()

    last_pull = time.monotonic()

    try:
        while not stop:
            time.sleep(debounce)

            changed, deleted = watcher.drain()
            if changed or deleted:
                log.info(
                    "local changes: %d modified, %d deleted",
                    len(changed),
                    len(deleted),
                )
                push_changes(sync_dir, changed, deleted, client)

            if time.monotonic() - last_pull >= pull_interval:
                pending = watcher.peek_changed()
                touched = pull_current(sync_dir, client, pending_local=pending)
                echo_guard.mark(touched)
                last_pull = time.monotonic()
    finally:
        watcher.stop()
        log.info("stopped")


@click.command()
@click.option(
    "--dir",
    "sync_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Local directory to sync (default: ~/vault-sync or SYNC_DIR env).",
)
@click.option(
    "--server",
    default=None,
    help="KB server URL (default: http://localhost:8000 or KB_SERVER_URL env).",
)
@click.option(
    "--interval",
    type=float,
    default=None,
    help="Pull interval in seconds (default: 30 or SYNC_PULL_INTERVAL_SECONDS env).",
)
@click.option(
    "--debounce",
    type=float,
    default=None,
    help="Debounce interval in seconds (default: 2 or SYNC_DEBOUNCE_SECONDS env).",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def main(
    sync_dir: Path | None,
    server: str | None,
    interval: float | None,
    debounce: float | None,
    verbose: bool,
) -> None:
    """Sync a local directory with the kb-server current view."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    settings = Settings()
    resolved_dir = sync_dir or settings.sync_dir
    resolved_server = server or settings.kb_server_url
    resolved_interval = interval if interval is not None else settings.sync_pull_interval_seconds
    resolved_debounce = debounce if debounce is not None else settings.sync_debounce_seconds

    if resolved_server != settings.kb_server_url:
        settings.kb_server_url = resolved_server

    client = KBClient(settings)

    click.echo(f"vault-sync: {resolved_dir} <-> {resolved_server}")
    click.echo(f"  debounce={resolved_debounce}s  pull_interval={resolved_interval}s")

    _run_loop(resolved_dir, client, resolved_debounce, resolved_interval)


if __name__ == "__main__":
    main()
