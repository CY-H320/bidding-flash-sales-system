#!/bin/bash

# Bidding Load Test - Zero Authentication During Test
# This version pre-authenticates ALL users before the test starts
# Compatible with WSL and Linux

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}?對?  $1${NC}"; }
print_success() { echo -e "${GREEN}??$1${NC}"; }
print_warning() { echo -e "${YELLOW}??  $1${NC}"; }

# Configuration
HOST=${1:-"http://biddingflashsalesalb-1838681311.ap-southeast-2.elb.amazonaws.com"}
USERS=${2:-1000}
SPAWN_RATE=${3:-100}
DURATION=${4:-5m}

echo ""
echo "============================================================"
echo "? BIDDING LOAD TEST"
echo "============================================================"
echo "This version:"
echo "  ??Pre-authenticates users BEFORE test"
echo "  ??ZERO login/register during test"
echo "  ??100% of requests are BIDS"
echo ""
echo "Configuration:"
echo "  Host:        $HOST"
echo "  Users:       $USERS"
echo "  Spawn Rate:  $SPAWN_RATE/sec"
echo "  Duration:    $DURATION"
echo "============================================================"
echo ""

# Check for virtual environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    print_warning "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Ensure locust is installed
print_info "Installing/verifying dependencies..."
pip install -q -r requirements.txt

# Create test users if needed
print_info "Ensuring test users exist..."
python create_test_users.py "$HOST" 50 2>/dev/null || true

# Ensure active session exists
print_info "Ensuring active session exists..."
python setup_test_session.py "$HOST" || exit 1

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
# Use ExtremeBiddingUser for 100% bidding (no leaderboard checks)
locust -f locustfile.py \
    --host="$HOST" \
    --users "$USERS" \
    --spawn-rate "$SPAWN_RATE" \
    --run-time "$DURATION" \
    --headless \
    --html "$RESULTS_DIR/report.html" \
    --csv "$RESULTS_DIR/results" \
    ExtremeBiddingUser

# Show results
echo ""
echo "============================================================"
print_success "Test Complete!"
echo "============================================================"
echo ""
print_info "Results saved to:"
echo "  ?? HTML: $RESULTS_DIR/report.html"
echo "  ?? CSV:  $RESULTS_DIR/results_stats.csv"
echo ""

# Wait a moment for files to be written
sleep 0.5

# Check if CSV files exist and have content
if [ -f "$RESULTS_DIR/results_stats.csv" ]; then
    FILE_SIZE=$(stat -f%z "$RESULTS_DIR/results_stats.csv" 2>/dev/null || stat -c%s "$RESULTS_DIR/results_stats.csv" 2>/dev/null || echo "0")
    if [ "$FILE_SIZE" -gt 100 ]; then
        echo "Quick Stats:"
        grep -E "POST|GET|Aggregated" "$RESULTS_DIR/results_stats.csv" 2>/dev/null | while IFS=, read -r type name req fail med avg min max size rps fps rest; do
            if [ -n "$req" ] && [ "$req" -gt 0 ]; then
                echo "  $type $name - Requests: $req, Avg Response: ${avg}ms"
            fi
        done
    else
        echo "?? Test Output Summary (from console):"
        # Results shown above in test output
    fi
    echo ""
else
    echo "??  Results CSV file not found"
    echo ""
fi

# Open report
if command -v open &> /dev/null; then
    read -p "Open HTML report? (y/n) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && open "$RESULTS_DIR/report.html"
fi

print_success "Done! ??"
