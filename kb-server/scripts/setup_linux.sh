#!/usr/bin/env bash

# End-to-end setup for kb-server on a fresh Linux machine.
# This script installs system dependencies, provisions PostgreSQL,
# installs Python dependencies, runs migrations, and performs checks.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# -----------------------------
# Configurable values (override with env vars)
# -----------------------------
DB_NAME="${DB_NAME:-kb}"
DB_USER="${DB_USER:-kb}"
DB_PASS="${DB_PASS:-kb}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
VAULT_PATH="${VAULT_PATH:-/srv/flightdeck/vault}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_DEV_DEPS="${INSTALL_DEV_DEPS:-true}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"
CREATE_ENV_FILE="${CREATE_ENV_FILE:-true}"

DATABASE_URL="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
VENV_DIR="$PROJECT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
VENV_ALEMBIC="$VENV_DIR/bin/alembic"
VENV_REVUP="$VENV_DIR/bin/revup"
VENV_UVICORN="$VENV_DIR/bin/uvicorn"

# -----------------------------
# Step tracking and reporting
# -----------------------------
declare -a STEP_NAMES=()
declare -a STEP_RESULTS=()
OVERALL_SUCCESS=true

print_banner() {
  echo
  echo "========================================"
  echo "$1"
  echo "========================================"
}

run_step() {
  local step_name="$1"
  shift

  STEP_NAMES+=("$step_name")
  echo
  echo ">>> $step_name"
  if "$@"; then
    STEP_RESULTS+=("SUCCESS")
    echo "✔ $step_name: SUCCESS"
  else
    STEP_RESULTS+=("FAILED")
    OVERALL_SUCCESS=false
    echo "✘ $step_name: FAILED"
  fi
}

print_summary() {
  print_banner "SETUP SUMMARY"

  local i
  for i in "${!STEP_NAMES[@]}"; do
    printf "%-45s %s\n" "${STEP_NAMES[$i]}" "${STEP_RESULTS[$i]}"
  done

  echo
  if [ "$OVERALL_SUCCESS" = "true" ]; then
    echo "OVERALL: SUCCESS"
    return 0
  fi

  echo "OVERALL: FAILED"
  return 1
}

# -----------------------------
# Helpers
# -----------------------------
needs_cmd() {
  command -v "$1" >/dev/null 2>&1
}

is_true() {
  [ "${1,,}" = "true" ] || [ "$1" = "1" ] || [ "${1,,}" = "yes" ]
}

SUDO=""
setup_sudo() {
  if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
  elif needs_cmd sudo; then
    SUDO="sudo"
  else
    echo "sudo is required when not running as root."
    return 1
  fi
}

PKG_MANAGER=""
POSTGRES_SERVICE=""
POSTGRES_VERSION_SUFFIX=""

detect_package_manager() {
  if needs_cmd apt-get; then
    PKG_MANAGER="apt"
    POSTGRES_SERVICE="postgresql"
    POSTGRES_VERSION_SUFFIX="15"
  elif needs_cmd dnf; then
    PKG_MANAGER="dnf"
    POSTGRES_SERVICE="postgresql"
    POSTGRES_VERSION_SUFFIX=""
  elif needs_cmd yum; then
    PKG_MANAGER="yum"
    POSTGRES_SERVICE="postgresql"
    POSTGRES_VERSION_SUFFIX=""
  elif needs_cmd zypper; then
    PKG_MANAGER="zypper"
    POSTGRES_SERVICE="postgresql"
    POSTGRES_VERSION_SUFFIX=""
  elif needs_cmd pacman; then
    PKG_MANAGER="pacman"
    POSTGRES_SERVICE="postgresql"
    POSTGRES_VERSION_SUFFIX=""
  else
    echo "Unsupported Linux distribution: no known package manager found."
    return 1
  fi
}

install_packages() {
  case "$PKG_MANAGER" in
    apt)
      $SUDO apt-get update
      $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y \
        git curl ca-certificates build-essential pkg-config software-properties-common \
        postgresql postgresql-client libpq-dev

      $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3 python3-venv python3-dev python3-pip
      ;;
    dnf)
      $SUDO dnf install -y \
        git curl ca-certificates gcc gcc-c++ make pkgconfig \
        python3 python3-virtualenv python3-pip \
        postgresql postgresql-server postgresql-contrib postgresql-devel
      ;;
    yum)
      $SUDO yum install -y \
        git curl ca-certificates gcc gcc-c++ make pkgconfig \
        python3 python3-pip \
        postgresql postgresql-server postgresql-contrib postgresql-devel
      ;;
    zypper)
      $SUDO zypper --non-interactive install \
        git curl ca-certificates gcc gcc-c++ make pkg-config \
        python3 python3-virtualenv python3-pip \
        postgresql postgresql-server postgresql-devel
      ;;
    pacman)
      $SUDO pacman -Sy --noconfirm \
        git curl ca-certificates base-devel \
        python python-pip python-virtualenv \
        postgresql postgresql-libs
      ;;
    *)
      echo "Internal error: unknown package manager '$PKG_MANAGER'"
      return 1
      ;;
  esac
}

ensure_python_version() {
  needs_cmd "$PYTHON_BIN" || {
    echo "Configured PYTHON_BIN not found: $PYTHON_BIN"
    return 1
  }

  "$PYTHON_BIN" - <<'PY'
import sys
major, minor = sys.version_info[:2]
print(f"Detected Python: {major}.{minor}")
if (major, minor) < (3, 10):
    print("Python 3.10+ is required.")
    raise SystemExit(1)
PY
}

ensure_postgres_user_exists() {
  if id postgres >/dev/null 2>&1; then
    return 0
  fi
  echo "System user 'postgres' not found. PostgreSQL may not be installed correctly."
  return 1
}

ensure_venv_exists() {
  if [ -x "$VENV_PYTHON" ] && [ -x "$VENV_PIP" ]; then
    return 0
  fi
  echo "Virtualenv not found at $VENV_DIR. Setup step likely failed."
  return 1
}

ensure_cmd_or_fail() {
  local cmd="$1"
  needs_cmd "$cmd" || {
    echo "Required command not found: $cmd"
    return 1
  }
}

init_postgres_if_needed() {
  case "$PKG_MANAGER" in
    dnf|yum)
      if [ ! -d /var/lib/pgsql/data/base ]; then
        if needs_cmd postgresql-setup; then
          $SUDO postgresql-setup --initdb
        elif needs_cmd postgresql-setup --help >/dev/null 2>&1; then
          $SUDO postgresql-setup initdb
        elif [ -x /usr/pgsql/bin/postgresql-setup ]; then
          $SUDO /usr/pgsql/bin/postgresql-setup initdb
        fi
      fi
      ;;
    pacman)
      if [ ! -f /var/lib/postgres/data/PG_VERSION ]; then
        $SUDO -u postgres initdb -D /var/lib/postgres/data
      fi
      ;;
    *)
      # apt/zypper usually initialize automatically.
      ;;
  esac
}

start_postgres() {
  ensure_cmd_or_fail psql || return 1
  ensure_postgres_user_exists || return 1
  init_postgres_if_needed || return 1

  if needs_cmd systemctl; then
    $SUDO systemctl enable --now "$POSTGRES_SERVICE"
    $SUDO systemctl is-active --quiet "$POSTGRES_SERVICE"
  else
    echo "systemctl not found; attempting pg_isready direct check."
  fi

  needs_cmd pg_isready || {
    echo "pg_isready not found after package installation."
    return 1
  }

  pg_isready -h "$DB_HOST" -p "$DB_PORT"
}

setup_postgres_user_and_db() {
  ensure_cmd_or_fail psql || return 1
  ensure_postgres_user_exists || return 1

  local psql_cmd
  psql_cmd="psql -v ON_ERROR_STOP=1"

  $SUDO -u postgres bash -lc "$psql_cmd <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}';
  ELSE
    ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';
  END IF;
END
\$\$;
SQL"

  if ! $SUDO -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
    $SUDO -u postgres createdb -O "${DB_USER}" "${DB_NAME}"
  fi
}

setup_python_env() {
  cd "$PROJECT_DIR" || return 1

  "$PYTHON_BIN" -m venv "$VENV_DIR" || return 1
  ensure_venv_exists || return 1
  "$VENV_PYTHON" -m pip install --upgrade pip wheel setuptools || return 1

  if is_true "$INSTALL_DEV_DEPS"; then
    if ! "$VENV_PIP" install -e ".[dev]"; then
      echo "Dependency installation failed. If error mentions Python version,"
      echo "check pyproject.toml requires-python and align it with your runtime."
      return 1
    fi
  else
    if ! "$VENV_PIP" install -e .; then
      echo "Dependency installation failed. If error mentions Python version,"
      echo "check pyproject.toml requires-python and align it with your runtime."
      return 1
    fi
  fi

  # Revup is required for stacked-diff workflow.
  "$VENV_PIP" install revup || return 1
}

upsert_env_file() {
  cd "$PROJECT_DIR" || return 1

  if is_true "$CREATE_ENV_FILE" && [ ! -f .env ]; then
    cp .env.example .env
  fi

  [ -f .env ] || {
    echo ".env not found and CREATE_ENV_FILE is false."
    return 1
  }

  if grep -q '^DATABASE_URL=' .env; then
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${DATABASE_URL}|" .env
  else
    echo "DATABASE_URL=${DATABASE_URL}" >> .env
  fi

  if grep -q '^VAULT_PATH=' .env; then
    sed -i "s|^VAULT_PATH=.*|VAULT_PATH=${VAULT_PATH}|" .env
  else
    echo "VAULT_PATH=${VAULT_PATH}" >> .env
  fi
}

setup_vault_repo() {
  if [ ! -d "$VAULT_PATH" ]; then
    $SUDO mkdir -p "$VAULT_PATH"
    $SUDO chown -R "$(id -un):$(id -gn)" "$VAULT_PATH"
  fi

  if [ ! -d "$VAULT_PATH/.git" ]; then
    git -C "$VAULT_PATH" init
  fi
}

run_migrations() {
  cd "$PROJECT_DIR" || return 1
  ensure_venv_exists || return 1
  export DATABASE_URL
  [ -x "$VENV_ALEMBIC" ] || {
    echo "alembic not found in venv: $VENV_ALEMBIC"
    return 1
  }
  "$VENV_ALEMBIC" upgrade head
}

run_checks() {
  cd "$PROJECT_DIR" || return 1
  ensure_venv_exists || return 1

  [ -x "$VENV_UVICORN" ] || {
    echo "uvicorn not found in venv: $VENV_UVICORN"
    return 1
  }
  "$VENV_UVICORN" --version >/dev/null
  "$VENV_PYTHON" - <<PY
import os
from pathlib import Path
db = os.environ.get("DATABASE_URL", "${DATABASE_URL}")
vault = Path("${VAULT_PATH}")
print("DATABASE_URL configured:", bool(db))
print("VAULT_PATH exists:", vault.exists())
print("VAULT_PATH git repo:", (vault / ".git").exists())
if not vault.exists() or not (vault / ".git").exists():
    raise SystemExit(1)
PY

  ensure_cmd_or_fail psql || return 1
  PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c 'SELECT 1;' >/dev/null
}

print_next_steps() {
  cat <<EOF

Next steps:
  1) Authenticate revup once:
       "$VENV_REVUP" config github_oauth
  2) Start API:
       cd "$PROJECT_DIR"
       "$VENV_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  3) Start worker (new terminal):
       cd "$PROJECT_DIR"
       "$VENV_PYTHON" -m app.workers.autosave
  4) Validate:
       curl http://localhost:8000/health
       curl http://localhost:8000/ready
EOF
}

main() {
  print_banner "KB SERVER LINUX SETUP"
  echo "Project directory: $PROJECT_DIR"
  echo "Database URL: $DATABASE_URL"
  echo "Vault path: $VAULT_PATH"

  run_step "Check running on Linux" bash -lc '[ "$(uname -s)" = "Linux" ]'
  run_step "Check sudo/root privileges" setup_sudo
  run_step "Detect package manager" detect_package_manager
  run_step "Install system packages" install_packages
  run_step "Validate Python >= 3.11" ensure_python_version
  run_step "Enable/start PostgreSQL service" start_postgres
  run_step "Create/update DB user and database" setup_postgres_user_and_db
  run_step "Create Python virtualenv and install deps" setup_python_env
  run_step "Create/update .env with DB and vault" upsert_env_file
  run_step "Create vault directory and git repo" setup_vault_repo

  if is_true "$RUN_MIGRATIONS"; then
    run_step "Run Alembic migrations" run_migrations
  else
    STEP_NAMES+=("Run Alembic migrations")
    STEP_RESULTS+=("SKIPPED")
  fi

  run_step "Run final setup checks" run_checks

  print_summary
  local code=$?
  print_next_steps
  exit "$code"
}

main "$@"
