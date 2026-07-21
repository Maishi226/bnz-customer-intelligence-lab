#!/usr/bin/env bash
set -euo pipefail

LAB_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$LAB_DIR/.." && pwd)"
LOG_DIR="$LAB_DIR/logs"
mkdir -p "$LOG_DIR"

set -a
source "$LAB_DIR/.env"
set +a

SEGMENT_DIR="${SEGMENT_REPO_DIR:-$WORKSPACE_DIR/bank-segmentation-service}"
MARKETING_DIR="${MARKETING_REPO_DIR:-$WORKSPACE_DIR/bnz-ai-marketing-hybrid}"

cleanup() {
  echo
  echo "Stopping BNZ demo services..."
  kill "${SEGMENT_PID:-}" "${MARKETING_PID:-}" "${LAB_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [[ ! -x "$SEGMENT_DIR/.venv/bin/python" ]]; then
  echo "Missing segmentation virtual environment: $SEGMENT_DIR/.venv"
  exit 1
fi
if [[ ! -x "$MARKETING_DIR/.venv/bin/uvicorn" ]]; then
  echo "Missing marketing virtual environment: $MARKETING_DIR/.venv"
  exit 1
fi
if [[ ! -x "$LAB_DIR/.venv/bin/uvicorn" ]]; then
  echo "Missing Lab virtual environment: $LAB_DIR/.venv"
  exit 1
fi

for required in BEDROCK_EVALUATION_MODEL_ID AWS_PROFILE AWS_REGION LEX_BOT_ID LEX_BOT_ALIAS_ID LEX_LOCALE_ID; do
  if [[ -z "${!required:-}" ]]; then
    echo "Missing required setting in .env: $required"
    exit 1
  fi
done

echo "Checking AWS SSO session..."
if ! aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION" >/dev/null 2>&1; then
  echo "AWS login is not active. Run this first:"
  echo "aws sso login --profile $AWS_PROFILE"
  exit 1
fi

stop_port() {
  local port="$1"
  local pids
  pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    echo "Stopping old service on port $port..."
    kill $pids 2>/dev/null || true
    for attempt in {1..20}; do
      lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1 || return 0
      sleep 0.25
    done
    echo "Could not stop the old service on port $port"
    exit 1
  fi
}

stop_port 8000
stop_port 8010
stop_port 8020

echo "Starting bank-segmentation-service on port 8000..."
(cd "$SEGMENT_DIR" && exec .venv/bin/python -m app.main) >"$LOG_DIR/segmentation.log" 2>&1 &
SEGMENT_PID=$!

echo "Starting bnz-ai-marketing-hybrid on port 8010..."
(cd "$MARKETING_DIR" && exec .venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8010) >"$LOG_DIR/marketing.log" 2>&1 &
MARKETING_PID=$!

echo "Starting Customer Intelligence Lab on port 8020..."
(cd "$LAB_DIR" && exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8020) >"$LOG_DIR/lab.log" 2>&1 &
LAB_PID=$!

for attempt in {1..20}; do
  SEGMENT_OK=0; MARKETING_OK=0; LAB_OK=0
  curl -fsS --max-time 1 http://127.0.0.1:8000/health >/dev/null 2>&1 && SEGMENT_OK=1 || true
  curl -fsS --max-time 1 http://127.0.0.1:8010/api/health >/dev/null 2>&1 && MARKETING_OK=1 || true
  curl -fsS --max-time 1 http://127.0.0.1:8020/api/health >/dev/null 2>&1 && LAB_OK=1 || true
  [[ "$SEGMENT_OK" == 1 && "$MARKETING_OK" == 1 && "$LAB_OK" == 1 ]] && break
  sleep 1
done

if [[ "$SEGMENT_OK" != 1 || "$MARKETING_OK" != 1 || "$LAB_OK" != 1 ]]; then
  echo "One or more services failed to start: segmentation=$SEGMENT_OK marketing=$MARKETING_OK lab=$LAB_OK"
  echo "Recent logs:"
  tail -20 "$LOG_DIR"/*.log 2>/dev/null || true
  exit 1
fi

LAB_HEALTH=$(curl -fsS http://127.0.0.1:8020/api/health)
if [[ "$LAB_HEALTH" != *'"bedrock_evaluation":"configured"'* || "$LAB_HEALTH" != *'"lex":"configured"'* ]]; then
  echo "Lab started, but Bedrock evaluation or Lex was not loaded from .env:"
  echo "$LAB_HEALTH"
  exit 1
fi

echo
echo "BNZ demo is running with Amazon Bedrock and Lex configured."
echo "Open: http://127.0.0.1:8020"
echo "Keep this window open. Press Control-C to stop all services."
echo "Logs: $LOG_DIR"
echo

open "http://127.0.0.1:8020"
wait
