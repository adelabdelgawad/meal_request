#!/bin/bash
#
# Debug Task Trigger Script
# Captures logs before, during, and after manual task execution
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="${BACKEND_DIR:-/home/adel/Desktop/meal_request/src/backend}"
API_URL="${API_URL:-http://localhost:8000}"
LOG_FILE="${LOG_FILE:-/tmp/app.log}"
DEBUG_OUTPUT_DIR="${DEBUG_OUTPUT_DIR:-$BACKEND_DIR/debug_traces}"

# Ensure debug output directory exists
mkdir -p "$DEBUG_OUTPUT_DIR"

# Timestamp for this test run
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_ID="test_${TIMESTAMP}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Scheduler Task Execution Debug Script               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if backend is running
echo -e "${YELLOW}[1/7]${NC} Checking backend status..."
if ! curl -s -f "$API_URL/health" > /dev/null 2>&1; then
    if ! curl -s -f "$API_URL/docs" > /dev/null 2>&1; then
        echo -e "${RED}ERROR: Backend not running at $API_URL${NC}"
        echo "Please start the backend with:"
        echo "  cd $BACKEND_DIR"
        echo "  PYTHONPATH=$BACKEND_DIR python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"
        exit 1
    fi
fi
echo -e "${GREEN}✓${NC} Backend is running"
echo ""

# Get admin token
echo -e "${YELLOW}[2/7]${NC} Authenticating..."
read -p "Admin Username (default: admin): " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}
read -sp "Admin Password: " ADMIN_PASS
echo ""

if [ -z "$ADMIN_PASS" ]; then
    echo -e "${RED}ERROR: Password required${NC}"
    exit 1
fi

# Login and get token
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/security/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\",\"scope\":\"local\"}")

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.accessToken // .access_token // empty')

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
    echo -e "${RED}ERROR: Authentication failed${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓${NC} Authenticated as $ADMIN_USER"
echo ""

# List available jobs
echo -e "${YELLOW}[3/7]${NC} Fetching available jobs..."
JOBS_RESPONSE=$(curl -s -X GET "$API_URL/api/v1/scheduler/jobs?page=1&per_page=10" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

echo "Available jobs:"
echo "$JOBS_RESPONSE" | jq -r '.data[] | "\(.id) - \(.nameEn // .name_en) (\(.jobKey // .job_key))"' | nl

echo ""
read -p "Enter Job ID to trigger: " JOB_ID

if [ -z "$JOB_ID" ]; then
    echo -e "${RED}ERROR: Job ID required${NC}"
    exit 1
fi

# Get job details
JOB_DETAILS=$(echo "$JOBS_RESPONSE" | jq -r ".data[] | select(.id == $JOB_ID)")
JOB_KEY=$(echo "$JOB_DETAILS" | jq -r '.jobKey // .job_key')
JOB_NAME=$(echo "$JOB_DETAILS" | jq -r '.nameEn // .name_en')

if [ -z "$JOB_KEY" ] || [ "$JOB_KEY" == "null" ]; then
    echo -e "${RED}ERROR: Job not found${NC}"
    exit 1
fi

echo -e "${GREEN}Selected:${NC} $JOB_NAME ($JOB_KEY)"
echo ""

# Pre-test database state
echo -e "${YELLOW}[4/7]${NC} Capturing pre-test database state..."
cat > "$DEBUG_OUTPUT_DIR/${TEST_ID}_pre_state.sql" << EOF
-- Pre-test database state snapshot
-- Test ID: $TEST_ID
-- Job ID: $JOB_ID
-- Job Key: $JOB_KEY
-- Timestamp: $(date -Iseconds)

-- Active scheduler instances
SELECT 'ACTIVE_INSTANCES' AS query_name, instance_name, host_name, status, last_heartbeat
FROM scheduler_instance
WHERE status = 'running';

-- Pending/running executions for target job
SELECT 'PENDING_EXECUTIONS' AS query_name, execution_id, status_id, started_at, executor_id
FROM scheduled_job_execution
WHERE job_id = $JOB_ID
  AND status_id IN (1, 2);

-- Job configuration
SELECT 'JOB_CONFIG' AS query_name, id, name_en, job_key, is_enabled, max_instances, last_run_at
FROM scheduled_job
WHERE id = $JOB_ID;
EOF

echo -e "${GREEN}✓${NC} Pre-test state saved to: $DEBUG_OUTPUT_DIR/${TEST_ID}_pre_state.sql"
echo ""

# Start log capture
echo -e "${YELLOW}[5/7]${NC} Starting log capture..."

# Try to find log file
if [ ! -f "$LOG_FILE" ]; then
    # Check common locations
    for possible_log in "/var/log/app.log" "/var/log/uvicorn.log" "$BACKEND_DIR/logs/app.log" "/tmp/meal_request.log"; do
        if [ -f "$possible_log" ]; then
            LOG_FILE="$possible_log"
            break
        fi
    done
fi

if [ -f "$LOG_FILE" ]; then
    echo "Capturing logs from: $LOG_FILE"
    # Start background log capture
    tail -f "$LOG_FILE" 2>/dev/null | grep -E "(job_id|job_key|execution_id|$JOB_KEY)" > "$DEBUG_OUTPUT_DIR/${TEST_ID}_raw_logs.txt" &
    LOG_CAPTURE_PID=$!
    echo "Log capture PID: $LOG_CAPTURE_PID"
else
    echo -e "${YELLOW}WARNING: Log file not found, will use API response only${NC}"
    LOG_CAPTURE_PID=""
fi

# Wait a moment for log capture to start
sleep 1
echo ""

# Trigger the job
echo -e "${YELLOW}[6/7]${NC} Triggering job: $JOB_NAME (ID: $JOB_ID)"
echo -e "${BLUE}Starting execution at: $(date -Iseconds)${NC}"
echo ""

TRIGGER_START=$(date +%s%N)

TRIGGER_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/scheduler/jobs/$JOB_ID/action" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"action":"trigger"}')

TRIGGER_END=$(date +%s%N)
TRIGGER_DURATION_MS=$(( ($TRIGGER_END - $TRIGGER_START) / 1000000 ))

echo "$TRIGGER_RESPONSE" | jq '.'

EXECUTION_ID=$(echo "$TRIGGER_RESPONSE" | jq -r '.executionId // .execution_id // empty')

if [ -z "$EXECUTION_ID" ] || [ "$EXECUTION_ID" == "null" ]; then
    echo -e "${RED}ERROR: Failed to trigger job${NC}"
    echo "Response: $TRIGGER_RESPONSE"
    [ -n "$LOG_CAPTURE_PID" ] && kill $LOG_CAPTURE_PID 2>/dev/null
    exit 1
fi

echo ""
echo -e "${GREEN}✓${NC} Job triggered successfully!"
echo -e "   Execution ID: ${BLUE}$EXECUTION_ID${NC}"
echo -e "   API Response Time: ${TRIGGER_DURATION_MS}ms"
echo ""

# Wait for execution to complete or timeout
echo -e "${YELLOW}[7/7]${NC} Monitoring execution..."
echo "Waiting for task to complete (timeout: 60s)..."

MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))

    # Check execution status
    HISTORY_RESPONSE=$(curl -s -X GET "$API_URL/api/v1/scheduler/jobs/$JOB_ID/history?page=1&per_page=5" \
        -H "Authorization: Bearer $ACCESS_TOKEN")

    EXEC_STATUS=$(echo "$HISTORY_RESPONSE" | jq -r ".data[] | select(.executionId == \"$EXECUTION_ID\") | .status" | head -1)

    if [ "$EXEC_STATUS" == "success" ] || [ "$EXEC_STATUS" == "SUCCESS" ]; then
        echo -e "${GREEN}✓${NC} Execution completed successfully!"
        break
    elif [ "$EXEC_STATUS" == "failed" ] || [ "$EXEC_STATUS" == "FAILED" ]; then
        echo -e "${RED}✗${NC} Execution failed"
        break
    fi

    echo -n "."
done

echo ""
echo ""

# Stop log capture
if [ -n "$LOG_CAPTURE_PID" ]; then
    sleep 2  # Give logs time to flush
    kill $LOG_CAPTURE_PID 2>/dev/null || true
    wait $LOG_CAPTURE_PID 2>/dev/null || true
fi

# Post-test database state
echo "Capturing post-test database state..."

cat > "$DEBUG_OUTPUT_DIR/${TEST_ID}_post_state.sql" << EOF
-- Post-test database state snapshot
-- Test ID: $TEST_ID
-- Job ID: $JOB_ID
-- Execution ID: $EXECUTION_ID
-- Timestamp: $(date -Iseconds)

-- All executions created during test
SELECT 'TEST_EXECUTIONS' AS query_name,
       execution_id,
       status_id,
       started_at,
       completed_at,
       TIMESTAMPDIFF(MICROSECOND, started_at, completed_at) / 1000 AS duration_ms,
       executor_id,
       error_message
FROM scheduled_job_execution
WHERE job_id = $JOB_ID
  AND started_at >= DATE_SUB(NOW(), INTERVAL 1 MINUTE)
ORDER BY started_at;

-- Lock records
SELECT 'LOCK_RECORDS' AS query_name,
       job_id,
       execution_id,
       executor_id,
       acquired_at,
       released_at,
       TIMESTAMPDIFF(MICROSECOND, acquired_at, released_at) / 1000 AS lock_duration_ms
FROM scheduled_job_lock
WHERE job_id = $JOB_ID
  AND acquired_at >= DATE_SUB(NOW(), INTERVAL 1 MINUTE)
ORDER BY acquired_at;
EOF

# Process logs
echo "Processing captured logs..."

if [ -f "$DEBUG_OUTPUT_DIR/${TEST_ID}_raw_logs.txt" ]; then
    # Extract JSON logs
    grep -E '\{.*\}' "$DEBUG_OUTPUT_DIR/${TEST_ID}_raw_logs.txt" | \
        jq -s 'sort_by(.timestamp_ns)' > "$DEBUG_OUTPUT_DIR/${TEST_ID}_structured_logs.json" 2>/dev/null || true
fi

# Generate summary
cat > "$DEBUG_OUTPUT_DIR/${TEST_ID}_summary.txt" << EOF
╔════════════════════════════════════════════════════════════╗
║           Task Execution Debug Summary                     ║
╚════════════════════════════════════════════════════════════╝

Test ID:          $TEST_ID
Timestamp:        $(date -Iseconds)
Job ID:           $JOB_ID
Job Key:          $JOB_KEY
Job Name:         $JOB_NAME
Execution ID:     $EXECUTION_ID
API Response:     ${TRIGGER_DURATION_MS}ms
Final Status:     $EXEC_STATUS

Files Generated:
  - Pre-state SQL:     ${TEST_ID}_pre_state.sql
  - Post-state SQL:    ${TEST_ID}_post_state.sql
  - Raw logs:          ${TEST_ID}_raw_logs.txt
  - Structured logs:   ${TEST_ID}_structured_logs.json
  - Summary:           ${TEST_ID}_summary.txt

Location: $DEBUG_OUTPUT_DIR

Next Steps:
  1. Review structured logs: jq '.' $DEBUG_OUTPUT_DIR/${TEST_ID}_structured_logs.json
  2. Run database queries from pre/post state SQL files
  3. Analyze timing between events
  4. Look for LOCK_FAILED or duplicate DUPLICATE_CHECK_PASSED events

EOF

cat "$DEBUG_OUTPUT_DIR/${TEST_ID}_summary.txt"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Debug trace completed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "To analyze logs:"
echo -e "  ${BLUE}jq '.' $DEBUG_OUTPUT_DIR/${TEST_ID}_structured_logs.json${NC}"
echo ""
echo "To populate debug document:"
echo -e "  ${BLUE}./scripts/populate_debug_doc.sh $TEST_ID${NC}"
echo ""
