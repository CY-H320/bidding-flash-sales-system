# PowerShell script to build frontend Docker image
# Usage: .\deploy\scripts\build_frontend_image.ps1
# Or with custom tag: TAG=v1 .\deploy\scripts\build_frontend_image.ps1

param(
    [string]$Tag = "bidding-frontend:latest",
    [string]$Context = "frontend",
    [string]$Dockerfile = "frontend/Dockerfile"
)

# Override with environment variable if set
if ($env:TAG) {
    $Tag = $env:TAG
}
if ($env:CONTEXT) {
    $Context = $env:CONTEXT
}
if ($env:DOCKERFILE) {
    $Dockerfile = $env:DOCKERFILE
}

Write-Host "Building frontend image: $Tag" -ForegroundColor Cyan
Write-Host "Context: $Context" -ForegroundColor Gray
Write-Host "Dockerfile: $Dockerfile" -ForegroundColor Gray

# Run docker build
docker build -f "$Dockerfile" -t "$Tag" "$Context"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Build completed successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ Build failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
