# PowerShell script to build backend Docker image
# Usage: .\deploy\scripts\build_backend_image.ps1
# Or with custom tag: TAG=v1 .\deploy\scripts\build_backend_image.ps1

param(
    [string]$Tag = "bidding-api:latest",
    [string]$Context = "backend",
    [string]$Dockerfile = "backend/DockerFile"
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

Write-Host "Building backend image: $Tag" -ForegroundColor Cyan
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
