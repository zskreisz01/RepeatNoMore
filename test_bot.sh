#!/bin/bash

echo "=== Bot Diagnostics ==="
echo ""

# 1. Check endpoint
ENDPOINT="https://aghastly-rhotic-marcela.ngrok-free.dev/api/webhook"  # Update this
echo "1. Testing endpoint: $ENDPOINT"
curl -s -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{"type":"message","text":"test"}' | jq . || echo "✗ Failed"
echo ""

# 2. Check local API
echo "2. Testing local API: http://localhost:8001/api/health"
curl -s http://localhost:8001/api/health | jq . || echo "✗ Failed"
echo ""

# 3. Check environment
echo "3. Checking environment variables:"
echo "MICROSOFT_APP_ID: ${MICROSOFT_APP_ID:0:10}..."
echo "MICROSOFT_APP_PASSWORD: ${MICROSOFT_APP_PASSWORD:0:10}..."
echo "MICROSOFT_APP_TYPE: $MICROSOFT_APP_TYPE"
echo ""

# 4. Check Docker
echo "4. Checking Docker containers:"
docker-compose ps
echo ""

# 5. Check logs
echo "5. Recent logs:"
docker-compose logs --tail=20 framework_agent | tail -10