#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${MARKETPILOT_RUNTIME_DIR:-"$ROOT_DIR/.runtime"}"
PID_DIR="$RUNTIME_DIR/pids"
LOG_DIR="$RUNTIME_DIR/logs"

FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
CELERY_LOG_LEVEL="${CELERY_LOG_LEVEL:-info}"

mkdir -p "$PID_DIR" "$LOG_DIR"

log() {
  printf '[MarketPilot] %s\n' "$*"
}

need_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

copy_env_if_missing() {
  local example_file="$1"
  local target_file="$2"

  if [[ ! -f "$target_file" ]]; then
    cp "$example_file" "$target_file"
    log "Created ${target_file#$ROOT_DIR/}"
  fi
}

pid_is_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
}

pid_file_is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && pid_is_running "$(cat "$pid_file")"
}

pid_cwd() {
  local pid="$1"
  lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1
}

pid_is_under_repo() {
  local pid="$1"
  local cwd
  cwd="$(pid_cwd "$pid" || true)"
  [[ "$cwd" == "$ROOT_DIR"* ]]
}

pid_for_port() {
  local port="$1"
  lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1
}

adopt_port_process_if_running() {
  local name="$1"
  local port="$2"
  local pid_file="$3"
  local pid

  pid="$(pid_for_port "$port" || true)"
  if [[ -z "$pid" ]]; then
    return 1
  fi

  if pid_is_under_repo "$pid"; then
    printf '%s\n' "$pid" > "$pid_file"
    log "$name already running on port $port; adopted PID $pid"
    return 0
  fi

  printf '%s port %s is already used by PID %s outside this repo.\n' "$name" "$port" "$pid" >&2
  exit 1
}

find_celery_pid() {
  local pid
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    if pid_is_under_repo "$pid"; then
      printf '%s\n' "$pid"
      return 0
    fi
  done < <(pgrep -f 'celery.*app.workers.celery_app' 2>/dev/null || true)
  return 1
}

start_process() {
  local name="$1"
  local pid_file="$2"
  local log_file="$3"
  local workdir="$4"
  shift 4

  if pid_file_is_running "$pid_file"; then
    log "$name already running with PID $(cat "$pid_file")"
    return 0
  fi

  log "Starting $name..."
  python3 - "$pid_file" "$log_file" "$workdir" "$@" <<'PY'
import os
import subprocess
import sys

pid_file, log_file, workdir, *command = sys.argv[1:]
log_fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
try:
    process = subprocess.Popen(
        command,
        cwd=workdir,
        stdin=subprocess.DEVNULL,
        stdout=log_fd,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
finally:
    os.close(log_fd)

with open(pid_file, "w", encoding="utf-8") as file:
    file.write(f"{process.pid}\n")
PY

  sleep 1
  if ! pid_file_is_running "$pid_file"; then
    printf '%s failed to start. Recent log:\n' "$name" >&2
    tail -n 80 "$log_file" >&2 || true
    exit 1
  fi

  log "$name started with PID $(cat "$pid_file")"
}

wait_url() {
  local name="$1"
  local url="$2"
  local attempts="${3:-40}"

  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "$name is reachable: $url"
      return 0
    fi
    sleep 1
  done

  printf '%s did not become reachable: %s\n' "$name" "$url" >&2
  exit 1
}

wait_container_healthy() {
  local container="$1"

  for _ in $(seq 1 40); do
    if [[ "$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || true)" == "healthy" ]]; then
      log "$container is healthy"
      return 0
    fi
    sleep 1
  done

  printf 'Container did not become healthy: %s\n' "$container" >&2
  docker inspect -f '{{json .State}}' "$container" 2>/dev/null || true
  exit 1
}

need_command docker
need_command npm
need_command python3
need_command curl

copy_env_if_missing "$ROOT_DIR/infra/.env.example" "$ROOT_DIR/infra/.env"
copy_env_if_missing "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
copy_env_if_missing "$ROOT_DIR/frontend/.env.example" "$ROOT_DIR/frontend/.env.local"

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  log "Installing frontend dependencies..."
  (cd "$ROOT_DIR/frontend" && npm install)
fi

if [[ ! -x "$ROOT_DIR/backend/.venv/bin/python" ]]; then
  log "Creating backend virtualenv..."
  (cd "$ROOT_DIR/backend" && python3 -m venv .venv)
fi

if [[ ! -x "$ROOT_DIR/backend/.venv/bin/uvicorn" || ! -x "$ROOT_DIR/backend/.venv/bin/celery" ]]; then
  log "Installing backend dependencies..."
  (
    cd "$ROOT_DIR/backend"
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -e ".[dev]"
  )
fi

log "Starting dependency services..."
docker compose --env-file "$ROOT_DIR/infra/.env" -f "$ROOT_DIR/infra/compose.yaml" up -d
wait_container_healthy marketpilot-postgres
wait_container_healthy marketpilot-redis
wait_container_healthy marketpilot-minio

BACKEND_PID_FILE="$PID_DIR/backend-api.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
CELERY_PID_FILE="$PID_DIR/celery-worker.pid"

if ! adopt_port_process_if_running "Backend API" "$BACKEND_PORT" "$BACKEND_PID_FILE"; then
  start_process \
    "Backend API" \
    "$BACKEND_PID_FILE" \
    "$LOG_DIR/backend-api.log" \
    "$ROOT_DIR/backend" \
    "$ROOT_DIR/backend/.venv/bin/uvicorn" app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
fi
wait_url "Backend API" "http://$BACKEND_HOST:$BACKEND_PORT/api/v1/health"

if [[ -f "$CELERY_PID_FILE" ]] && pid_file_is_running "$CELERY_PID_FILE"; then
  log "Celery worker already running with PID $(cat "$CELERY_PID_FILE")"
elif existing_celery_pid="$(find_celery_pid)"; then
  printf '%s\n' "$existing_celery_pid" > "$CELERY_PID_FILE"
  log "Celery worker already running; adopted PID $existing_celery_pid"
else
  start_process \
    "Celery worker" \
    "$CELERY_PID_FILE" \
    "$LOG_DIR/celery-worker.log" \
    "$ROOT_DIR/backend" \
    "$ROOT_DIR/backend/.venv/bin/celery" -A app.workers.celery_app worker --loglevel="$CELERY_LOG_LEVEL"
fi

if ! adopt_port_process_if_running "Frontend" "$FRONTEND_PORT" "$FRONTEND_PID_FILE"; then
  start_process \
    "Frontend" \
    "$FRONTEND_PID_FILE" \
    "$LOG_DIR/frontend.log" \
    "$ROOT_DIR/frontend" \
    npm run dev -- --hostname "$FRONTEND_HOST" --port "$FRONTEND_PORT"
fi
wait_url "Frontend" "http://$FRONTEND_HOST:$FRONTEND_PORT"

log "Startup complete."
log "Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT"
log "Backend health: http://$BACKEND_HOST:$BACKEND_PORT/api/v1/health"
log "Logs: ${LOG_DIR#$ROOT_DIR/}"
