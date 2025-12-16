#!/bin/bash

#================================================================
# Concurrent Trigger Test Script
#================================================================
# Purpose: Trigger the same job twice simultaneously to test
#          for race conditions and cascade issues
#
# Usage: ./scripts/concurrent_trigger.sh <JOB_ID>
#
# Example: ./scripts/concurrent_trigger.sh 4
#================================================================

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
LOGIN_ENDPOINT="/api/v1/auth/login"
TRIGGER_ENDPOINT="/api/v1/scheduler/jobs"
LOG_DIR="debug_traces"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_ID="concurrent_${TIMESTAMP}"

# Create log directory
mkdir -p "$LOG_DIR"

echo -e "${BLUE}=== Concurrent Trigger Test ===${NC}"
echo "Test ID: $TEST_ID"
echo "Timestamp: $(date -Iseconds)"
echo ""

# Check if job ID is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Job ID required${NC}"
    echo "Usage: $0 <JOB_ID>"
    echo ""
    echo "Example: $0 4"
    exit 1
fi

JOB_ID="$1"

# Prompt for credentials
echo -e "${YELLOW}Enter admin credentials:${NC}"
read -p "Username [admin]: " USERNAME
USERNAME=${USERNAME:-admin}
read -sp "Password: " PASSWORD
echo ""

# Create payload file
cat > /tmp/concurrent_login_payload.json << EOF
{
  "username": "$USERNAME",
  "password": "$PASSWORD",
  "scope": "local"
}
EOF

echo -e "${BLUE}[1/6] Authenticating...${NC}"

# Get authentication token
AUTH_RESPONSE=$(curl -s -X POST "${BACKEND_URL}${LOGIN_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d @/tmp/concurrent_login_payload.json)

TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.accessToken // empty')

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Authentication failed${NC}"
    echo "$AUTH_RESPONSE" | jq '.'
    rm -f /tmp/concurrent_login_payload.json
    exit 1
fi

echo -e "${GREEN}✓ Authenticated successfully${NC}"
echo ""

# Verify job exists
echo -e "${BLUE}[2/6] Verifying job ID $JOB_ID...${NC}"

JOB_INFO=$(curl -s -X GET "${BACKEND_URL}${TRIGGER_ENDPOINT}/${JOB_ID}" \
  -H "Authorization: Bearer $TOKEN")

JOB_KEY=$(echo "$JOB_INFO" | jq -r '.jobKey // empty')

if [ -z "$JOB_KEY" ]; then
    echo -e "${RED}✗ Job ID $JOB_ID not found${NC}"
    echo "$JOB_INFO" | jq '.'
    rm -f /tmp/concurrent_login_payload.json
    exit 1
fi

JOB_NAME=$(echo "$JOB_INFO" | jq -r '.nameEn')
echo -e "${GREEN}✓ Found job: $JOB_NAME ($JOB_KEY)${NC}"
echo ""

# Start log capture
echo -e "${BLUE}[3/6] Starting log capture...${NC}"

LOG_FILE="/tmp/uvicorn.log"
if [ ! -f "$LOG_FILE" ]; then
    LOG_FILE="/var/log/app.log"
    if [ ! -f "$LOG_FILE" ]; then
        LOG_FILE="logs/app.log"
    fi
fi

echo "Monitoring log file: $LOG_FILE"

# Start background log capture
tail -f "$LOG_FILE" 2>/dev/null | grep -E "job_id.*$JOB_ID|job_key.*$JOB_KEY|DUPLICATE_CHECK|EXEC_CREATE|LOCK_" > "${LOG_DIR}/${TEST_ID}_live.log" &
LOG_CAPTURE_PID=$!

echo -e "${GREEN}✓ Log capture started (PID: $LOG_CAPTURE_PID)${NC}"
echo ""

# Trigger job twice simultaneously
echo -e "${BLUE}[4/6] Triggering job twice simultaneously...${NC}"
echo "Job ID: $JOB_ID"
echo "Trigger time: $(date -Iseconds)"
echo ""

# Create temporary scripts for parallel execution
cat > /tmp/trigger_1.sh << EOF
#!/bin/bash
curl -s -X POST "${BACKEND_URL}${TRIGGER_ENDPOINT}/${JOB_ID}/action" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"trigger"}' \
  > "${LOG_DIR}/${TEST_ID}_trigger_1_response.json"
EOF

cat > /tmp/trigger_2.sh << EOF
#!/bin/bash
curl -s -X POST "${BACKEND_URL}${TRIGGER_ENDPOINT}/${JOB_ID}/action" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"trigger"}' \
  > "${LOG_DIR}/${TEST_ID}_trigger_2_response.json"
EOF

chmod +x /tmp/trigger_1.sh /tmp/trigger_2.sh

# Execute both triggers simultaneously
TRIGGER_START=$(date +%s%N)
/tmp/trigger_1.sh & PID1=$!
/tmp/trigger_2.sh & PID2=$!

# Wait for both to complete
wait $PID1
wait $PID2
TRIGGER_END=$(date +%s%N)

TRIGGER_DURATION_MS=$(( (TRIGGER_END - TRIGGER_START) / 1000000 ))

echo -e "${GREEN}✓ Both triggers sent (duration: ${TRIGGER_DURATION_MS}ms)${NC}"
echo ""

# Extract execution IDs
EXEC_ID_1=$(jq -r '.executionId // empty' "${LOG_DIR}/${TEST_ID}_trigger_1_response.json")
EXEC_ID_2=$(jq -r '.executionId // empty' "${LOG_DIR}/${TEST_ID}_trigger_2_response.json")

echo "Response 1:"
jq '.' "${LOG_DIR}/${TEST_ID}_trigger_1_response.json" | head -5
echo ""

echo "Response 2:"
jq '.' "${LOG_DIR}/${TEST_ID}_trigger_2_response.json" | head -5
echo ""

# Monitor for completion
echo -e "${BLUE}[5/6] Monitoring execution(s)...${NC}"

for i in {1..30}; do
    sleep 1

    # Check status
    STATUS_RESPONSE=$(curl -s -X GET "${BACKEND_URL}${TRIGGER_ENDPOINT}/${JOB_ID}" \
      -H "Authorization: Bearer $TOKEN")

    CURRENT_STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.currentExecutionStatus // "none"')
    CURRENT_EXEC_ID=$(echo "$STATUS_RESPONSE" | jq -r '.currentExecutionId // "none"')

    echo "[$i] Status: $CURRENT_STATUS (exec: ${CURRENT_EXEC_ID:0:8}...)"

    if [ "$CURRENT_STATUS" == "none" ] || [ "$CURRENT_STATUS" == "null" ]; then
        echo -e "${GREEN}✓ Execution completed${NC}"
        break
    fi
done

echo ""

# Stop log capture
echo -e "${BLUE}[6/6] Stopping log capture and analyzing...${NC}"

kill $LOG_CAPTURE_PID 2>/dev/null || true
sleep 1

echo -e "${GREEN}✓ Log capture stopped${NC}"
echo ""

# Extract structured logs
echo -e "${BLUE}Extracting structured logs...${NC}"

grep '"event":' "$LOG_FILE" | grep -E "$JOB_KEY|$EXEC_ID_1|$EXEC_ID_2" > "${LOG_DIR}/${TEST_ID}_structured.log" 2>/dev/null || true

# Count DUPLICATE_CHECK_PASSED events
DUPLICATE_CHECKS=$(grep 'DUPLICATE_CHECK_PASSED' "${LOG_DIR}/${TEST_ID}_structured.log" 2>/dev/null | wc -l)
LOCK_FAILURES=$(grep 'LOCK_FAILED' "${LOG_DIR}/${TEST_ID}_structured.log" 2>/dev/null | wc -l)
EXEC_CREATES=$(grep 'EXEC_CREATE_START' "${LOG_DIR}/${TEST_ID}_structured.log" 2>/dev/null | wc -l)

echo ""
echo -e "${BLUE}=== Analysis ===${NC}"
echo ""
echo "Execution IDs:"
echo "  Request 1: $EXEC_ID_1"
echo "  Request 2: $EXEC_ID_2"
echo ""
echo "Event Counts:"
echo "  DUPLICATE_CHECK_PASSED: $DUPLICATE_CHECKS"
echo "  EXEC_CREATE_START: $EXEC_CREATES"
echo "  LOCK_FAILED: $LOCK_FAILURES"
echo ""

if [ "$DUPLICATE_CHECKS" -gt 1 ]; then
    echo -e "${RED}⚠ CASCADE DETECTED!${NC}"
    echo "  Multiple duplicate checks passed ($DUPLICATE_CHECKS)"
    echo ""

    if [ "$LOCK_FAILURES" -gt 0 ]; then
        echo -e "${YELLOW}  Lock mechanism prevented duplicate execution ($LOCK_FAILURES failures)${NC}"
    else
        echo -e "${RED}  WARNING: No lock failures detected - both may have executed!${NC}"
    fi
else
    echo -e "${GREEN}✓ No cascade detected${NC}"
    echo "  Only one execution was created"
fi

echo ""
echo -e "${BLUE}=== Output Files ===${NC}"
echo ""
echo "  ${LOG_DIR}/${TEST_ID}_trigger_1_response.json"
echo "  ${LOG_DIR}/${TEST_ID}_trigger_2_response.json"
echo "  ${LOG_DIR}/${TEST_ID}_live.log"
echo "  ${LOG_DIR}/${TEST_ID}_structured.log"
echo ""

# Cleanup
rm -f /tmp/concurrent_login_payload.json /tmp/trigger_1.sh /tmp/trigger_2.sh

echo -e "${GREEN}=== Test Complete ===${NC}"
echo ""
echo "To view structured logs:"
echo "  cat ${LOG_DIR}/${TEST_ID}_structured.log"
echo ""
echo "To view detailed analysis:"
echo "  ./scripts/populate_debug_doc.sh $TEST_ID"
