# Bidding Load Test - Zero Authentication During Test
# This version pre-authenticates ALL users before the test starts
# PowerShell version for Windows

$ErrorActionPreference = "Stop"

# Colors
$Green = "`e[0;32m"
$Yellow = "`e[1;33m"
$Blue = "`e[0;34m"
$Reset = "`e[0m"

function Print-Info {
    param([string]$Message)
    Write-Host "$Blue`ℹ️  $Message$Reset"
}

function Print-Success {
    param([string]$Message)
    Write-Host "$Green`✅ $Message$Reset"
}

function Print-Warning {
    param([string]$Message)
    Write-Host "$Yellow`⚠️  $Message$Reset"
}

# Configuration
$Host_Param = if ($args.Count -gt 0) { $args[0] } else { "http://biddingflashsalesalb-1838681311.ap-southeast-2.elb.amazonaws.com" }
$Users = if ($args.Count -gt 1) { $args[1] } else { 100 }
$SpawnRate = if ($args.Count -gt 2) { $args[2] } else { 10 }
$Duration = if ($args.Count -gt 3) { $args[3] } else { "5m" }

Write-Host ""
Write-Host "============================================================"
Write-Host "🎯 BIDDING LOAD TEST"
Write-Host "============================================================"
Write-Host "This version:"
Write-Host "  ✅ Pre-authenticates users BEFORE test"
Write-Host "  ✅ ZERO login/register during test"
Write-Host "  ✅ 100% of requests are BIDS"
Write-Host ""
Write-Host "Configuration:"
Write-Host "  Host:        $Host_Param"
Write-Host "  Users:       $Users"
Write-Host "  Spawn Rate:  $SpawnRate/sec"
Write-Host "  Duration:    $Duration"
Write-Host "============================================================"
Write-Host ""

# Ensure locust and dependencies are installed
Print-Info "Checking and installing dependencies..."
& pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Print-Warning "Retrying pip install..."
    & python pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies"
        exit 1
    }
}

# Create test users if needed
Print-Info "Ensuring test users exist..."
try {
    & python create_test_users.py "$Host_Param" 50 2>&1 | Out-Null
} catch {
    # Skip if fails
}

# Ensure active session exists
Print-Info "Ensuring active session exists..."
& python setup_test_session.py "$Host_Param"
if ($LASTEXITCODE -ne 0) {
    exit 1
}

# Confirm
Write-Host ""
Print-Warning "Ready to launch $Users concurrent bidders"
Read-Host "Press Enter to continue or Ctrl+C to cancel"
Write-Host ""

# Create results directory
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ResultsDir = "results_$Timestamp"
New-Item -ItemType Directory -Path $ResultsDir -Force | Out-Null

Print-Info "Starting test... (duration: $Duration)"
Write-Host ""

# Run the test
# Use ExtremeBiddingUser for 100% bidding (no leaderboard checks)
$TestOutput = & locust -f locustfile.py `
    --host="$Host_Param" `
    --users $Users `
    --spawn-rate $SpawnRate `
    --run-time "$Duration" `
    --headless `
    --html "$ResultsDir/report.html" `
    --csv "$ResultsDir/results" `
    ExtremeBiddingUser 2>&1

# Check if test was successful
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================================"
    Print-Success "Test Complete!"
    Write-Host "============================================================"
} else {
    Write-Host ""
    Write-Host "============================================================"
    Print-Warning "Test Completed with status code: $LASTEXITCODE"
    Write-Host "============================================================"
}
Write-Host ""
Print-Info "Results saved to:"
Write-Host "  📊 HTML: $ResultsDir/report.html"
Write-Host "  📈 CSV:  $ResultsDir/results_stats.csv"
Write-Host ""

# Wait a moment for files to be written
Start-Sleep -Milliseconds 500

# Check if CSV files exist and have content
$CsvStatsFile = "$ResultsDir/results_stats.csv"
$CsvHistoryFile = "$ResultsDir/results_history.csv"

Write-Host "📋 Checking result files..."
if (Test-Path $CsvStatsFile) {
    $StatsSize = (Get-Item $CsvStatsFile).Length
    Write-Host "  ✅ Stats file exists: $StatsSize bytes"
    
    # Try to read the file
    $StatsContent = Get-Content $CsvStatsFile -ErrorAction SilentlyContinue
    if ($StatsContent -and $StatsContent.Count -gt 1) {
        Write-Host "  ✅ Stats file has data"
    } else {
        Write-Host "  ⚠️  Stats file appears empty or has only headers"
        Write-Host ""
        Write-Host "📊 Test Output Summary (from console):"
        $TestOutput | Select-String "BID|Aggregated" | ForEach-Object { Write-Host "  $_" }
    }
} else {
    Write-Host "  ⚠️  Stats file not found"
}

if (Test-Path $CsvHistoryFile) {
    $HistorySize = (Get-Item $CsvHistoryFile).Length
    Write-Host "  ✅ History file exists: $HistorySize bytes"
} else {
    Write-Host "  ℹ️  History file not created (this is normal)"
}

# Quick stats
if (Test-Path "$ResultsDir/results_stats.csv") {
    Write-Host ""
    Write-Host "Quick Stats from CSV:"
    $StatsFile = Get-Content "$ResultsDir/results_stats.csv"
    $StatsFile | Select-String "POST|GET|Aggregated" | ForEach-Object {
        $Line = $_ -split ','
        if ($Line.Count -ge 9) {
            $type = $Line[0].Trim()
            $name = $Line[1].Trim()
            $req = $Line[2].Trim()
            $fail = $Line[3].Trim()
            $avg = $Line[5].Trim()
            
            if ($req -gt 0 -and $avg -gt 0) {
                Write-Host "  $type $name - Requests: $req, Avg Response: ${avg}ms"
            }
        }
    }
    Write-Host ""
}

# Open report
$OpenReport = Read-Host "Open HTML report? (y/n)"
if ($OpenReport -eq 'y' -or $OpenReport -eq 'Y') {
    $ReportPath = Join-Path (Get-Location) "$ResultsDir/report.html"
    Start-Process $ReportPath
}

Print-Success "Done! 🎉"
