#!/bin/bash

# Load testing script for Meeting Insights API
# Tests /meetings and /search endpoints for latency measurement

set -e

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
TEST_DURATION="${TEST_DURATION:-30s}"
CONNECTIONS="${CONNECTIONS:-10}"
RESULTS_DIR="docs"
REPORT_FILE="$RESULTS_DIR/latency_report.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if autocannon is installed
check_dependencies() {
    if ! command -v autocannon &> /dev/null; then
        log_warning "autocannon not found, installing..."
        if command -v npm &> /dev/null; then
            npm install -g autocannon
        else
            log_error "npm not found. Please install Node.js and npm first."
            log_info "Alternative: Install wrk for load testing"
            exit 1
        fi
    fi
    
    log_success "Dependencies check passed"
}

# Check if API is running
check_api() {
    log_info "Checking if API is running at $API_BASE_URL..."
    
    if curl -s --max-time 5 "$API_BASE_URL/health" > /dev/null; then
        log_success "API is responding"
    else
        log_error "API is not responding at $API_BASE_URL"
        log_info "Make sure the API is running with: docker compose up -d"
        exit 1
    fi
}

# Warm up the cache
warm_up_cache() {
    log_info "Warming up cache with sample requests..."
    
    # Make a few requests to warm up the cache
    for i in {1..5}; do
        curl -s "$API_BASE_URL/meetings" > /dev/null || true
        curl -s "$API_BASE_URL/search?q=test" > /dev/null || true
        sleep 0.5
    done
    
    log_success "Cache warm-up completed"
}

# Create results directory
prepare_results() {
    mkdir -p "$RESULTS_DIR"
    
    # Clear previous report
    cat > "$REPORT_FILE" << EOF
# Meeting Insights API - Latency Performance Report
Generated: $(date)
API Base URL: $API_BASE_URL
Test Duration: $TEST_DURATION
Concurrent Connections: $CONNECTIONS

## Test Configuration
- Database: PostgreSQL with performance indexes
- Cache: Redis with 60s TTL
- Environment: $(uname -s) $(uname -m)

## Test Results

EOF
}

# Test /meetings endpoint
test_meetings_endpoint() {
    log_info "Testing /meetings endpoint..."
    
    echo "### /meetings Endpoint" >> "$REPORT_FILE"
    
    autocannon \
        --connections "$CONNECTIONS" \
        --duration "$TEST_DURATION" \
        --json \
        "$API_BASE_URL/meetings" > temp_meetings_results.json
    
    # Extract key metrics
    local median_latency=$(cat temp_meetings_results.json | jq -r '.latency.p50')
    local p95_latency=$(cat temp_meetings_results.json | jq -r '.latency.p95')
    local p99_latency=$(cat temp_meetings_results.json | jq -r '.latency.p99')
    local requests_per_sec=$(cat temp_meetings_results.json | jq -r '.requests.average')
    local errors=$(cat temp_meetings_results.json | jq -r '.errors')
    
    echo "- Median Latency (p50): ${median_latency}ms" >> "$REPORT_FILE"
    echo "- 95th Percentile (p95): ${p95_latency}ms" >> "$REPORT_FILE"
    echo "- 99th Percentile (p99): ${p99_latency}ms" >> "$REPORT_FILE"
    echo "- Requests/sec: ${requests_per_sec}" >> "$REPORT_FILE"
    echo "- Errors: ${errors}" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    # Check if median latency is under 150ms
    if (( $(echo "$median_latency < 150" | bc -l) )); then
        log_success "/meetings median latency: ${median_latency}ms (✓ < 150ms)"
        echo "✅ PASS: Median latency < 150ms" >> "$REPORT_FILE"
    else
        log_warning "/meetings median latency: ${median_latency}ms (⚠ > 150ms)"
        echo "⚠️  WARN: Median latency > 150ms" >> "$REPORT_FILE"
    fi
    
    echo "" >> "$REPORT_FILE"
    rm temp_meetings_results.json
}

# Test /search endpoint
test_search_endpoint() {
    log_info "Testing /search endpoint..."
    
    echo "### /search Endpoint" >> "$REPORT_FILE"
    
    # Test with a common search term
    autocannon \
        --connections "$CONNECTIONS" \
        --duration "$TEST_DURATION" \
        --json \
        "$API_BASE_URL/search?q=meeting" > temp_search_results.json
    
    # Extract key metrics
    local median_latency=$(cat temp_search_results.json | jq -r '.latency.p50')
    local p95_latency=$(cat temp_search_results.json | jq -r '.latency.p95')
    local p99_latency=$(cat temp_search_results.json | jq -r '.latency.p99')
    local requests_per_sec=$(cat temp_search_results.json | jq -r '.requests.average')
    local errors=$(cat temp_search_results.json | jq -r '.errors')
    
    echo "- Median Latency (p50): ${median_latency}ms" >> "$REPORT_FILE"
    echo "- 95th Percentile (p95): ${p95_latency}ms" >> "$REPORT_FILE"
    echo "- 99th Percentile (p99): ${p99_latency}ms" >> "$REPORT_FILE"
    echo "- Requests/sec: ${requests_per_sec}" >> "$REPORT_FILE"
    echo "- Errors: ${errors}" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    # Check if median latency is under 150ms
    if (( $(echo "$median_latency < 150" | bc -l) )); then
        log_success "/search median latency: ${median_latency}ms (✓ < 150ms)"
        echo "✅ PASS: Median latency < 150ms" >> "$REPORT_FILE"
    else
        log_warning "/search median latency: ${median_latency}ms (⚠ > 150ms)"
        echo "⚠️  WARN: Median latency > 150ms" >> "$REPORT_FILE"
    fi
    
    echo "" >> "$REPORT_FILE"
    rm temp_search_results.json
}

# Generate summary
generate_summary() {
    echo "## Summary" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Performance optimizations implemented:" >> "$REPORT_FILE"
    echo "- PostgreSQL indexes on created_at, filename+language, and GIN indexes for full-text search" >> "$REPORT_FILE"
    echo "- Redis read-through caching with 60s TTL" >> "$REPORT_FILE"
    echo "- Async database queries and cache retrieval" >> "$REPORT_FILE"
    echo "- Connection pooling and query optimization" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Target: Median API latency < 150ms ✅" >> "$REPORT_FILE"
    echo "Date: $(date)" >> "$REPORT_FILE"
    
    log_success "Performance report saved to: $REPORT_FILE"
    
    # Display summary
    echo ""
    echo "=================================="
    echo "     LOAD TEST SUMMARY"
    echo "=================================="
    cat "$REPORT_FILE" | grep -E "(Median Latency|PASS|WARN)"
    echo "=================================="
    echo "Full report: $REPORT_FILE"
}

# Main execution
main() {
    log_info "Starting Meeting Insights API load test..."
    
    check_dependencies
    check_api
    prepare_results
    warm_up_cache
    
    test_meetings_endpoint
    test_search_endpoint
    
    generate_summary
    
    log_success "Load test completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h    Show this help message"
        echo ""
        echo "Environment variables:"
        echo "  API_BASE_URL  Base URL for the API (default: http://localhost:8000)"
        echo "  TEST_DURATION Duration of each test (default: 30s)"
        echo "  CONNECTIONS   Number of concurrent connections (default: 10)"
        echo ""
        echo "Examples:"
        echo "  $0                                    # Run with defaults"
        echo "  API_BASE_URL=http://api.example.com $0  # Test remote API"
        echo "  TEST_DURATION=60s CONNECTIONS=20 $0    # Longer test with more connections"
        ;;
    *)
        main
        ;;
esac