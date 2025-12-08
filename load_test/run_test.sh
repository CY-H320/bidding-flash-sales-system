#!/bin/bash

# Bidding Load Test - Zero Authentication During Test
# This version pre-authenticates ALL users before the test starts

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# Configuration
HOST=${1:-"http://biddingflashsalesalb-1838681311.ap-southeast-2.elb.amazonaws.com"}
USERS=${2:-1000}
SPAWN_RATE=${3:-100}
DURATION=${4:-5m}

echo ""
echo "============================================================"
echo "🎯 BIDDING LOAD TEST"
echo "============================================================"
echo "This version:"
echo "  ✅ Pre-authenticates users BEFORE test"
echo "  ✅ ZERO login/register during test"
echo "  ✅ 100% of requests are BIDS"
echo ""
echo "Configuration:"
echo "  Host:        $HOST"
echo "  Users:       $USERS"
echo "  Spawn Rate:  $SPAWN_RATE/sec"
echo "  Duration:    $DURATION"
echo "============================================================"
echo ""

# Ensure locust is installed
if ! command -v locust &> /dev/null; then
    print_warning "Installing Locust..."
    pip3 install -r requirements.txt
fi

# Create test users if needed
print_info "Ensuring test users exist..."
python3 create_test_users.py "$HOST" 50 2>/dev/null || true

# Ensure active session exists
print_info "Ensuring active session exists..."
python3 setup_test_session.py "$HOST" || exit 1

# Confirm
echo ""
print_warning "Ready to launch $USERS concurrent bidders"
read -p "Press Enter to continue or Ctrl+C to cancel..."
echo ""

# Create results directory
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_DIR="results_${TIMESTAMP}"
mkdir -p "$RESULTS_DIR"

print_info "Starting test... (duration: $DURATION)"
echo ""

# Run the test
locust -f locustfile.py \
    --host="$HOST" \
    --users "$USERS" \
    --spawn-rate "$SPAWN_RATE" \
    --run-time "$DURATION" \
    --headless \
    --html "$RESULTS_DIR/report.html" \
    --csv "$RESULTS_DIR/results"

# Show results
echo ""
echo "============================================================"
print_success "Test Complete!"
echo "============================================================"
echo ""
print_info "Results saved to:"
echo "  📊 HTML: $RESULTS_DIR/report.html"
echo "  📈 CSV:  $RESULTS_DIR/results_stats.csv"
echo ""

# Quick stats
if [ -f "$RESULTS_DIR/results_stats.csv" ]; then
    echo "Quick Stats:"
    grep "BID" "$RESULTS_DIR/results_stats.csv" 2>/dev/null | while IFS=, read -r type name req fail med avg min max size rps fps rest; do
        fail_pct=$(awk "BEGIN {printf \"%.1f\", ($fail / $req) * 100}")
        echo "  Total Bids:       $req"
        echo "  Failures:         $fail ($fail_pct%)"
        echo "  Avg Response:     ${avg}ms"
        echo "  Throughput:       ${rps} req/s"
    done
    echo ""
fi

# Open report
if command -v open &> /dev/null; then
    read -p "Open HTML report? (y/n) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && open "$RESULTS_DIR/report.html"
fi

print_success "Done! 🎉"
