# PowerShell script to push Docker images to AWS ECR
# Usage: .\deploy\scripts\push_to_ecr.ps1
# Or with custom settings: TAG=v1 AWS_REGION=us-east-1 .\deploy\scripts\push_to_ecr.ps1

param(
    [string]$Tag = "v1",
    [string]$AwsRegion = "ap-southeast-2",
    [string]$AwsAccountId = "701055077457",
    [string]$RepositoryName = "bidding-flash-sales"
)

# Override with environment variables if set
if ($env:TAG) {
    $Tag = $env:TAG
}
if ($env:AWS_REGION) {
    $AwsRegion = $env:AWS_REGION
}
if ($env:AWS_ACCOUNT_ID) {
    $AwsAccountId = $env:AWS_ACCOUNT_ID
}
if ($env:REPOSITORY_NAME) {
    $RepositoryName = $env:REPOSITORY_NAME
}

# Validate AWS Account ID
if (-not $AwsAccountId) {
    Write-Host "✗ Error: AWS_ACCOUNT_ID is required" -ForegroundColor Red
    Write-Host "Usage: AWS_ACCOUNT_ID=123456789 .\deploy\scripts\push_to_ecr.ps1" -ForegroundColor Yellow
    exit 1
}

$EcrRegistry = "$AwsAccountId.dkr.ecr.$AwsRegion.amazonaws.com"
$BackendImageName = "bidding-api"
$FrontendImageName = "bidding-frontend"

Write-Host "Pushing images to ECR" -ForegroundColor Cyan
Write-Host "Registry: $EcrRegistry" -ForegroundColor Gray
Write-Host "Region: $AwsRegion" -ForegroundColor Gray
Write-Host "Tag: $Tag" -ForegroundColor Gray

# Check if AWS CLI is installed
Write-Host "`nChecking AWS CLI..." -ForegroundColor Yellow
$awsCommand = Get-Command aws -ErrorAction SilentlyContinue
if (-not $awsCommand) {
    Write-Host "✗ AWS CLI is not installed" -ForegroundColor Red
    Write-Host "`nPlease install AWS CLI:" -ForegroundColor Yellow
    Write-Host "  Option 1: Download from https://aws.amazon.com/cli/" -ForegroundColor Gray
    Write-Host "  Option 2: Use winget: winget install Amazon.AWSCLI" -ForegroundColor Gray
    Write-Host "  Option 3: Use chocolatey: choco install awscli" -ForegroundColor Gray
    exit 1
}

# Create ECR repositories if they don't exist
Write-Host "`nEnsuring ECR repositories exist..." -ForegroundColor Yellow

foreach ($repoName in @($BackendImageName, $FrontendImageName)) {
    $repoExists = aws ecr describe-repositories --region $AwsRegion --repository-names $repoName --query "repositories[0].repositoryName" 2>$null
    
    if (-not $repoExists) {
        Write-Host "Creating ECR repository: $repoName" -ForegroundColor Cyan
        aws ecr create-repository --repository-name $repoName --region $AwsRegion
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Repository created: $repoName" -ForegroundColor Green
        } else {
            Write-Host "✗ Failed to create repository: $repoName" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "✓ Repository already exists: $repoName" -ForegroundColor Green
    }
}

# Login to ECR
Write-Host "`nLogging in to ECR..." -ForegroundColor Yellow
$loginCommand = "aws ecr get-login-password --region $AwsRegion | docker login --username AWS --password-stdin $EcrRegistry"
Invoke-Expression $loginCommand

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to login to ECR" -ForegroundColor Red
    Write-Host "`nTroubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check AWS credentials: aws configure" -ForegroundColor Gray
    Write-Host "  2. Verify AWS region: $AwsRegion" -ForegroundColor Gray
    Write-Host "  3. Check IAM permissions for ECR" -ForegroundColor Gray
    exit 1
}

# Tag and push backend image
Write-Host "`nPushing backend image..." -ForegroundColor Yellow
$backendRemoteTag = "$EcrRegistry/$BackendImageName`:$Tag"
docker tag "$BackendImageName`:latest" $backendRemoteTag
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to tag backend image" -ForegroundColor Red
    Write-Host "Make sure image exists: docker images | grep bidding-api" -ForegroundColor Gray
    exit 1
}

docker push $backendRemoteTag
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Backend image pushed successfully: $backendRemoteTag" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to push backend image" -ForegroundColor Red
    exit 1
}

# Tag and push frontend image
Write-Host "`nPushing frontend image..." -ForegroundColor Yellow
$frontendRemoteTag = "$EcrRegistry/$FrontendImageName`:$Tag"
docker tag "$FrontendImageName`:latest" $frontendRemoteTag
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to tag frontend image" -ForegroundColor Red
    Write-Host "Make sure image exists: docker images | grep bidding-frontend" -ForegroundColor Gray
    exit 1
}

docker push $frontendRemoteTag
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Frontend image pushed successfully: $frontendRemoteTag" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to push frontend image" -ForegroundColor Red
    exit 1
}

Write-Host "`n✓ All images pushed successfully!" -ForegroundColor Green
