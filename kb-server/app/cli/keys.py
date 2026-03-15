"""CLI for managing API keys.

Usage:
    python -m app.cli.keys create --name "yash-laptop" --role user
    python -m app.cli.keys list
    python -m app.cli.keys revoke --prefix kbk_a1b2
"""

from __future__ import annotations

import argparse
import secrets
import sys
from datetime import datetime, timezone

from app.core.auth import _hash_key
from app.models.api_key import ApiKey
from app.models.db import SessionLocal, ensure_tables

VALID_ROLES = ("readonly", "user", "agent", "admin")


def _generate_key() -> str:
    """Generate a key in the format ``kbk_<32 hex chars>``."""
    return f"kbk_{secrets.token_hex(16)}"


def cmd_create(args: argparse.Namespace) -> None:
    if args.role not in VALID_ROLES:
        print(f"Error: role must be one of {VALID_ROLES}", file=sys.stderr)
        sys.exit(1)

    ensure_tables()
    plaintext = _generate_key()
    key_hash = _hash_key(plaintext)
    prefix = plaintext[:8]

    session = SessionLocal()
    try:
        row = ApiKey(
            key_hash=key_hash,
            prefix=prefix,
            name=args.name,
            role=args.role,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        print(f"Created API key (id={row.id}):")
        print(f"  Name:   {row.name}")
        print(f"  Role:   {row.role}")
        print(f"  Prefix: {row.prefix}")
        print()
        print(f"  Key:    {plaintext}")
        print()
        print("  Store this key securely — it cannot be retrieved again.")
    finally:
        session.close()


def cmd_list(args: argparse.Namespace) -> None:
    ensure_tables()
    session = SessionLocal()
    try:
        rows = session.query(ApiKey).order_by(ApiKey.created_at).all()
        if not rows:
            print("No API keys found.")
            return

        fmt = "{:<6} {:<12} {:<20} {:<10} {:<8} {:<20} {:<20}"
        header = fmt.format("ID", "Prefix", "Name", "Role", "Active", "Created", "Last Used")
        print(header)
        print("-" * len(header))
        for r in rows:
            created = r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else ""
            last_used = r.last_used_at.strftime("%Y-%m-%d %H:%M") if r.last_used_at else "never"
            active = "yes" if r.is_active else "REVOKED"
            print(fmt.format(r.id, r.prefix, r.name[:20], r.role, active, created, last_used))
    finally:
        session.close()


def cmd_revoke(args: argparse.Namespace) -> None:
    ensure_tables()
    session = SessionLocal()
    try:
        row = (
            session.query(ApiKey)
            .filter(ApiKey.prefix == args.prefix, ApiKey.is_active.is_(True))
            .first()
        )
        if row is None:
            print(f"No active key found with prefix '{args.prefix}'", file=sys.stderr)
            sys.exit(1)

        row.is_active = False
        row.revoked_at = datetime.now(timezone.utc)
        session.commit()
        print(f"Revoked key: {row.prefix} ({row.name}, role={row.role})")
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage KB Server API keys")
    sub = parser.add_subparsers(dest="command", required=True)

    create_p = sub.add_parser("create", help="Create a new API key")
    create_p.add_argument("--name", required=True, help="Label for this key")
    create_p.add_argument("--role", required=True, choices=VALID_ROLES, help="Key role")

    sub.add_parser("list", help="List all API keys")

    revoke_p = sub.add_parser("revoke", help="Revoke an API key")
    revoke_p.add_argument("--prefix", required=True, help="Key prefix (e.g., kbk_a1b2)")

    args = parser.parse_args()

    commands = {"create": cmd_create, "list": cmd_list, "revoke": cmd_revoke}
    commands[args.command](args)


if __name__ == "__main__":
    main()
