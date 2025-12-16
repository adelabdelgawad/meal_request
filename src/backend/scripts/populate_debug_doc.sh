#!/bin/bash
#
# Populate Debug Document from Captured Logs
# Analyzes structured logs and database state to fill in debug_task_execution.md
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BACKEND_DIR="${BACKEND_DIR:-/home/adel/Desktop/meal_request/src/backend}"
DEBUG_OUTPUT_DIR="${DEBUG_OUTPUT_DIR:-$BACKEND_DIR/debug_traces}"
DEBUG_DOC="$BACKEND_DIR/debug_task_execution.md"

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}ERROR: Test ID required${NC}"
    echo "Usage: $0 <test_id>"
    echo ""
    echo "Available test runs:"
    ls -1 "$DEBUG_OUTPUT_DIR" | grep "_summary.txt" | sed 's/_summary.txt//' | sed 's/test_/  /' || echo "  (none found)"
    exit 1
fi

TEST_ID="$1"

# Check if test files exist
STRUCTURED_LOGS="$DEBUG_OUTPUT_DIR/test_${TEST_ID}_structured_logs.json"
SUMMARY_FILE="$DEBUG_OUTPUT_DIR/test_${TEST_ID}_summary.txt"

if [ ! -f "$STRUCTURED_LOGS" ]; then
    echo -e "${RED}ERROR: Structured logs not found: $STRUCTURED_LOGS${NC}"
    exit 1
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      Debug Document Population Script                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Test ID: $TEST_ID"
echo "Logs: $STRUCTURED_LOGS"
echo ""

# Extract key information
echo -e "${YELLOW}[1/5]${NC} Extracting execution metadata..."

# Get first event (should be API_ENTRY or DUPLICATE_CHECK)
FIRST_EVENT=$(jq -r '.[0]' "$STRUCTURED_LOGS")
FIRST_TIMESTAMP_NS=$(echo "$FIRST_EVENT" | jq -r '.timestamp_ns')

# Extract job info
JOB_ID=$(jq -r '.[0].job_id // empty' "$STRUCTURED_LOGS")
JOB_KEY=$(jq -r '.[0].job_key // .[1].job_key // empty' "$STRUCTURED_LOGS")
USER_ID=$(jq -r '.[0].user_id // .[0].triggered_by_user_id // empty' "$STRUCTURED_LOGS")
CORRELATION_ID=$(jq -r '.[0].correlation_id // empty' "$STRUCTURED_LOGS")

# Count executions
EXEC_IDS=$(jq -r '.[] | select(.event == "EXEC_CREATE_START") | .execution_id' "$STRUCTURED_LOGS" | sort -u)
EXEC_COUNT=$(echo "$EXEC_IDS" | wc -l | tr -d ' ')

echo "  Job ID: $JOB_ID"
echo "  Job Key: $JOB_KEY"
echo "  User ID: $USER_ID"
echo "  Executions created: $EXEC_COUNT"

CASCADE_DETECTED="NO"
if [ "$EXEC_COUNT" -gt 1 ]; then
    CASCADE_DETECTED="YES"
    echo -e "  ${RED}⚠ CASCADE DETECTED!${NC}"
fi

echo ""

# Calculate timings
echo -e "${YELLOW}[2/5]${NC} Calculating event timings..."

# Function to calculate delta from first event
calc_delta() {
    local ts=$1
    echo $(( ($ts - $FIRST_TIMESTAMP_NS) / 1000000 ))
}

# Create timeline
TIMELINE_FILE=$(mktemp)

jq -r '.[] | "\(.timestamp_ns)|\(.event)|\(.execution_id // "N/A")|\(.message)"' "$STRUCTURED_LOGS" | \
while IFS='|' read -r ts event exec_id message; do
    delta=$(calc_delta $ts)
    echo "$delta|$event|$exec_id|$message"
done | sort -n > "$TIMELINE_FILE"

echo "  Timeline generated with $(wc -l < $TIMELINE_FILE) events"
echo ""

# Detect cascade pattern
echo -e "${YELLOW}[3/5]${NC} Analyzing cascade pattern..."

# Count duplicate checks
DUPLICATE_CHECKS=$(jq -r '.[] | select(.event == "DUPLICATE_CHECK_PASSED")' "$STRUCTURED_LOGS" | jq -s 'length')

if [ "$DUPLICATE_CHECKS" -gt 1 ]; then
    echo -e "  ${RED}⚠ Multiple duplicate checks passed: $DUPLICATE_CHECKS${NC}"

    # Calculate gap between checks
    FIRST_CHECK_NS=$(jq -r '.[] | select(.event == "DUPLICATE_CHECK_PASSED") | .timestamp_ns' "$STRUCTURED_LOGS" | head -1)
    SECOND_CHECK_NS=$(jq -r '.[] | select(.event == "DUPLICATE_CHECK_PASSED") | .timestamp_ns' "$STRUCTURED_LOGS" | tail -1)

    if [ "$FIRST_CHECK_NS" != "$SECOND_CHECK_NS" ]; then
        CHECK_GAP_MS=$(( ($SECOND_CHECK_NS - $FIRST_CHECK_NS) / 1000000 ))
        echo "  Gap between checks: ${CHECK_GAP_MS}ms"

        if [ "$CHECK_GAP_MS" -lt 100 ]; then
            echo -e "  ${RED}🚨 RACE CONDITION: Gap < 100ms${NC}"
            PATTERN="Race Condition"
        fi
    fi
fi

# Check lock failures
LOCK_FAILURES=$(jq -r '.[] | select(.event == "LOCK_FAILED")' "$STRUCTURED_LOGS" | jq -s 'length')

if [ "$LOCK_FAILURES" -gt 0 ]; then
    echo -e "  ${YELLOW}⚠ Lock failures detected: $LOCK_FAILURES${NC}"
    echo "  (Lock mechanism prevented duplicate execution)"
fi

echo ""

# Generate populated document
echo -e "${YELLOW}[4/5]${NC} Generating populated debug document..."

OUTPUT_DOC="$DEBUG_OUTPUT_DIR/test_${TEST_ID}_debug_populated.md"

# Start with template
cp "$DEBUG_DOC" "$OUTPUT_DOC"

# Function to replace placeholder
replace_placeholder() {
    local placeholder=$1
    local value=$2
    sed -i "s|\[$placeholder\]|$value|g" "$OUTPUT_DOC"
}

# Replace basic metadata
replace_placeholder "YYYY-MM-DD HH:MM:SS UTC" "$(date -Iseconds)"
replace_placeholder "job_key" "$JOB_KEY"
replace_placeholder "JOB_KEY" "$JOB_KEY"
replace_placeholder "job_id" "$JOB_ID"
replace_placeholder "JOB_ID" "$JOB_ID"
replace_placeholder "user_id or \"SCHEDULED\"" "${USER_ID:-SCHEDULED}"
replace_placeholder "USER_ID" "$USER_ID"
replace_placeholder "COUNT" "$EXEC_COUNT"

# Update cascade detection checkbox
if [ "$CASCADE_DETECTED" == "YES" ]; then
    sed -i 's/☐ YES ☑ NO/☑ YES ☐ NO/' "$OUTPUT_DOC"
fi

# Extract and insert individual events
API_ENTRY=$(jq -r '.[] | select(.event == "API_ENTRY")' "$STRUCTURED_LOGS" | head -1)
if [ -n "$API_ENTRY" ] && [ "$API_ENTRY" != "null" ]; then
    # Insert full API_ENTRY event JSON
    API_ENTRY_FORMATTED=$(echo "$API_ENTRY" | jq '.')
    # This is complex to do with sed, so we'll just append to the appendix
fi

# Add full timeline to appendix
cat >> "$OUTPUT_DOC" << EOF

## AUTOMATED ANALYSIS RESULTS

### Test Run: $TEST_ID
**Generated:** $(date -Iseconds)
**Cascade Detected:** $CASCADE_DETECTED
**Total Events:** $(jq 'length' "$STRUCTURED_LOGS")
**Executions Created:** $EXEC_COUNT

### Event Timeline (Auto-Generated)

| Delta (ms) | Event | Execution ID | Message |
|------------|-------|--------------|---------|
EOF

# Add timeline table
while IFS='|' read -r delta event exec_id message; do
    # Truncate message to 50 chars
    short_message=$(echo "$message" | cut -c1-50)
    echo "| $delta | $event | $exec_id | $short_message |" >> "$OUTPUT_DOC"
done < "$TIMELINE_FILE"

cat >> "$OUTPUT_DOC" << EOF

### Execution IDs Created

EOF

# List all execution IDs
echo "$EXEC_IDS" | while read -r exec_id; do
    echo "- \`$exec_id\`" >> "$OUTPUT_DOC"

    # Get events for this execution
    exec_events=$(jq -r ".[] | select(.execution_id == \"$exec_id\") | .event" "$STRUCTURED_LOGS" | tr '\n' ', ' | sed 's/,$//')
    echo "  - Events: $exec_events" >> "$OUTPUT_DOC"

    # Check status
    lock_status=$(jq -r ".[] | select(.execution_id == \"$exec_id\" and (.event == \"LOCK_ACQUIRED\" or .event == \"LOCK_FAILED\")) | .event" "$STRUCTURED_LOGS" | head -1)
    if [ "$lock_status" == "LOCK_ACQUIRED" ]; then
        echo "  - ✅ Lock: ACQUIRED (primary execution)" >> "$OUTPUT_DOC"
    elif [ "$lock_status" == "LOCK_FAILED" ]; then
        echo "  - ❌ Lock: FAILED (cascade blocked by lock)" >> "$OUTPUT_DOC"
    fi
done

cat >> "$OUTPUT_DOC" << EOF

### Pattern Analysis

EOF

if [ "$DUPLICATE_CHECKS" -gt 1 ]; then
    cat >> "$OUTPUT_DOC" << EOF
**🚨 RACE CONDITION DETECTED**

- Multiple duplicate checks passed: $DUPLICATE_CHECKS
- Gap between checks: ${CHECK_GAP_MS:-N/A}ms
- This indicates two concurrent requests both passed the duplicate check before either created an execution record

**Root Cause:** Race condition in duplicate check logic (lines 1082-1088 in scheduler_service.py)

**Fix Required:** Database-level unique constraint on (job_id, status='running')

EOF
fi

if [ "$LOCK_FAILURES" -gt 0 ]; then
    cat >> "$OUTPUT_DOC" << EOF
**✅ LOCK MECHANISM WORKING**

- Lock failures detected: $LOCK_FAILURES
- The distributed lock successfully prevented duplicate execution
- However, execution records were still created (database state pollution)

**Recommendation:** Move duplicate check to AFTER execution record creation with unique constraint

EOF
fi

# Add complete logs to appendix
cat >> "$OUTPUT_DOC" << EOF

### Complete Structured Logs (JSON)

\`\`\`json
$(jq '.' "$STRUCTURED_LOGS")
\`\`\`

EOF

echo "  Generated: $OUTPUT_DOC"
echo ""

# Generate analysis summary
echo -e "${YELLOW}[5/5]${NC} Generating analysis summary..."

ANALYSIS_FILE="$DEBUG_OUTPUT_DIR/test_${TEST_ID}_analysis.txt"

cat > "$ANALYSIS_FILE" << EOF
═══════════════════════════════════════════════════════════
        EXECUTION TRACE ANALYSIS SUMMARY
═══════════════════════════════════════════════════════════

Test ID:          $TEST_ID
Timestamp:        $(date -Iseconds)
Job ID:           $JOB_ID
Job Key:          $JOB_KEY
Correlation ID:   $CORRELATION_ID

─────────────────────────────────────────────────────────────
EXECUTION SUMMARY
─────────────────────────────────────────────────────────────

Total Events:              $(jq 'length' "$STRUCTURED_LOGS")
Executions Created:        $EXEC_COUNT
Duplicate Checks Passed:   $DUPLICATE_CHECKS
Lock Failures:             $LOCK_FAILURES

Cascade Detected:          $CASCADE_DETECTED

─────────────────────────────────────────────────────────────
EXECUTION IDS
─────────────────────────────────────────────────────────────

$EXEC_IDS

─────────────────────────────────────────────────────────────
EVENT TIMELINE
─────────────────────────────────────────────────────────────

$(column -t -s'|' < "$TIMELINE_FILE")

─────────────────────────────────────────────────────────────
FINDINGS
─────────────────────────────────────────────────────────────

EOF

if [ "$CASCADE_DETECTED" == "YES" ]; then
    cat >> "$ANALYSIS_FILE" << EOF
🚨 CASCADE DETECTED

Problem:
  Multiple execution records were created for the same job within a
  short time window, indicating a race condition or concurrent trigger.

Evidence:
  - $EXEC_COUNT execution records created
  - $DUPLICATE_CHECKS duplicate checks passed
  $([ "$DUPLICATE_CHECKS" -gt 1 ] && echo "  - Gap between checks: ${CHECK_GAP_MS}ms")

Root Cause Analysis:
  $(if [ "$DUPLICATE_CHECKS" -gt 1 ] && [ "${CHECK_GAP_MS:-999}" -lt 100 ]; then
      echo "RACE CONDITION: Two requests passed duplicate check simultaneously"
      echo "  The gap of ${CHECK_GAP_MS}ms indicates both requests checked for running"
      echo "  executions before either created their execution record."
  elif [ "$DUPLICATE_CHECKS" -gt 1 ]; then
      echo "CONCURRENT TRIGGERS: Multiple triggers within ${CHECK_GAP_MS}ms"
      echo "  Possible causes:"
      echo "  - Frontend double-click"
      echo "  - Manual trigger + APScheduler trigger"
      echo "  - Multiple scheduler instances"
  else
      echo "UNKNOWN: Further investigation required"
  fi)

Lock Mechanism Status:
  $(if [ "$LOCK_FAILURES" -gt 0 ]; then
      echo "✅ WORKING: Lock prevented $LOCK_FAILURES duplicate executions"
      echo "  However, execution records were still created (database pollution)"
  else
      echo "⚠️  NOT TESTED: No lock failures observed"
  fi)

Recommended Fix:
  1. Add database-level unique constraint on (job_id, status='running')
  2. Move duplicate check to AFTER execution creation (let DB enforce uniqueness)
  3. Handle IntegrityError gracefully with user-friendly message

EOF
else
    cat >> "$ANALYSIS_FILE" << EOF
✅ NO CASCADE DETECTED

The execution completed normally with a single execution record.

Timeline Summary:
  - API request received and processed
  - Duplicate check passed (no running execution found)
  - Execution record created
  - Lock acquired successfully
  - Task dispatched to Celery
  - Task completed successfully

EOF
fi

cat >> "$ANALYSIS_FILE" << EOF

─────────────────────────────────────────────────────────────
FILES GENERATED
─────────────────────────────────────────────────────────────

  Populated Debug Doc:    $OUTPUT_DOC
  Analysis Summary:       $ANALYSIS_FILE
  Structured Logs:        $STRUCTURED_LOGS
  Timeline:               $TIMELINE_FILE

─────────────────────────────────────────────────────────────
NEXT STEPS
─────────────────────────────────────────────────────────────

  1. Review populated debug document:
     less $OUTPUT_DOC

  2. Run database queries to verify execution state:
     cat $DEBUG_OUTPUT_DIR/test_${TEST_ID}_post_state.sql

  3. If cascade detected, implement recommended fixes

  4. Re-test after implementing fixes

═══════════════════════════════════════════════════════════

EOF

cat "$ANALYSIS_FILE"

# Cleanup
rm "$TIMELINE_FILE"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Analysis complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Review the populated debug document:"
echo -e "  ${BLUE}less $OUTPUT_DOC${NC}"
echo ""
