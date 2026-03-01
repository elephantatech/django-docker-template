#!/usr/bin/env bash
set -euo pipefail

# Integration test runner for Docker Compose
# Usage: ./scripts/run-integration-tests.sh

COMPOSE="docker compose"
WEB_CMD="/app/.venv/bin/python manage.py"
MAX_WAIT=60

cleanup() {
    echo ""
    echo "==> Shutting down services..."
    $COMPOSE down -v --remove-orphans 2>/dev/null
}
trap cleanup EXIT

echo "==> Building and starting services..."
$COMPOSE up -d --build

echo "==> Waiting for web service (up to ${MAX_WAIT}s)..."
elapsed=0
until curl -sf http://localhost:8000/api/health/ > /dev/null 2>&1; do
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        echo "ERROR: Web service failed to start within ${MAX_WAIT}s"
        $COMPOSE logs web
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo "    waiting... (${elapsed}s)"
done
echo "    Web service is ready."

echo ""
echo "==> Running migrations..."
$COMPOSE exec -T web $WEB_CMD migrate --no-input

echo ""
echo "==> Setting up permission groups..."
$COMPOSE exec -T web $WEB_CMD setup_groups

echo ""
echo "==> Running integration tests..."
$COMPOSE exec -T web $WEB_CMD test_integration

echo ""
echo "==> Verifying health endpoint..."
HEALTH=$(curl -sf http://localhost:8000/api/health/)
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
if [ "$STATUS" = "healthy" ]; then
    echo "    Health: $STATUS"
else
    echo "    ERROR: Health status is '$STATUS'"
    echo "    $HEALTH"
    exit 1
fi

echo ""
echo "==> Verifying Prometheus metrics endpoint..."
if curl -sf http://localhost:8000/metrics > /dev/null 2>&1; then
    echo "    Metrics endpoint: OK"
else
    echo "    ERROR: Metrics endpoint unreachable"
    exit 1
fi

echo ""
echo "==> Verifying Prometheus scraper..."
if curl -sf http://localhost:9090/-/ready > /dev/null 2>&1; then
    echo "    Prometheus: ready"
else
    echo "    ERROR: Prometheus is not ready"
    exit 1
fi

echo ""
echo "========================================"
echo "  All integration tests passed!"
echo "========================================"
