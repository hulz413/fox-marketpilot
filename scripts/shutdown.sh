#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${MARKETPILOT_RUNTIME_DIR:-"$ROOT_DIR/.runtime"}"
PID_DIR="$RUNTIME_DIR/pids"

FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

log() {
  printf '[MarketPilot] %s\n' "$*"
}

pid_is_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
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

child_pids() {
  pgrep -P "$1" 2>/dev/null || true
}

stop_pid_tree() {
  local pid="$1"
  local child

  if ! pid_is_running "$pid"; then
    return 0
  fi

  while read -r child; do
    [[ -z "$child" ]] && continue
    stop_pid_tree "$child"
  done < <(child_pids "$pid")

  kill "$pid" >/dev/null 2>&1 || true
}

force_kill_if_running() {
  local pid="$1"

  if pid_is_running "$pid"; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi
}

stop_pid_file() {
  local name="$1"
  local pid_file="$2"
  local pid

  if [[ ! -f "$pid_file" ]]; then
    return 0
  fi

  pid="$(cat "$pid_file")"
  if pid_is_running "$pid"; then
    log "Stopping $name with PID $pid..."
    stop_pid_tree "$pid"
    sleep 2
    force_kill_if_running "$pid"
  fi

  rm -f "$pid_file"
}

pid_for_port() {
  local port="$1"
  lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1
}

stop_port_process_under_repo() {
  local name="$1"
  local port="$2"
  local pid

  pid="$(pid_for_port "$port" || true)"
  if [[ -z "$pid" ]]; then
    return 0
  fi

  if pid_is_under_repo "$pid"; then
    log "Stopping $name on port $port with PID $pid..."
    stop_pid_tree "$pid"
    sleep 2
    force_kill_if_running "$pid"
  else
    log "Skipping $name on port $port; PID $pid is outside this repo."
  fi
}

stop_matching_under_repo() {
  local name="$1"
  local pattern="$2"
  local pid

  while read -r pid; do
    [[ -z "$pid" ]] && continue
    if pid_is_under_repo "$pid"; then
      log "Stopping $name with PID $pid..."
      stop_pid_tree "$pid"
      sleep 1
      force_kill_if_running "$pid"
    fi
  done < <(pgrep -f "$pattern" 2>/dev/null || true)
}

stop_pid_file "Frontend" "$PID_DIR/frontend.pid"
stop_pid_file "Backend API" "$PID_DIR/backend-api.pid"
stop_pid_file "Celery worker" "$PID_DIR/celery-worker.pid"

stop_port_process_under_repo "Frontend" "$FRONTEND_PORT"
stop_port_process_under_repo "Backend API" "$BACKEND_PORT"
stop_matching_under_repo "Celery worker" 'celery.*app.workers.celery_app'

if [[ -f "$ROOT_DIR/infra/.env" ]]; then
  log "Stopping dependency services..."
  docker compose --env-file "$ROOT_DIR/infra/.env" -f "$ROOT_DIR/infra/compose.yaml" down
else
  log "Stopping dependency services..."
  docker compose --env-file "$ROOT_DIR/infra/.env.example" -f "$ROOT_DIR/infra/compose.yaml" down
fi

log "Shutdown complete."
