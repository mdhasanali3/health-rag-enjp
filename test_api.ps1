# PowerShell API Testing Script for Healthcare RAG Assistant

$API_URL = "http://localhost:8000"
$API_KEY = if ($env:API_KEY) { $env:API_KEY } else { "dev-key-change-in-production" }

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Healthcare RAG API Test Script" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Endpoint,
        [string]$Data = $null,
        [string]$FilePath = $null
    )

    Write-Host "Testing: $Name" -ForegroundColor Yellow

    $headers = @{
        "X-API-Key" = $API_KEY
    }

    try {
        if ($Method -eq "GET") {
            $response = Invoke-RestMethod -Uri "$API_URL$Endpoint" -Method Get -Headers $headers
        }
        elseif ($FilePath) {
            # File upload
            $form = @{
                files = Get-Item -Path $FilePath
            }
            $response = Invoke-RestMethod -Uri "$API_URL$Endpoint" -Method Post -Headers $headers -Form $form
        }
        else {
            $headers["Content-Type"] = "application/json"
            $response = Invoke-RestMethod -Uri "$API_URL$Endpoint" -Method $Method -Headers $headers -Body $Data
        }

        Write-Host "✓ Success" -ForegroundColor Green
        $response | ConvertTo-Json -Depth 5

    }
    catch {
        Write-Host "✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
    }

    Write-Host ""
}

# Test 1: Health Check
Test-Endpoint -Name "Health Check" -Method "GET" -Endpoint "/health"

# Test 2: Root Endpoint
Test-Endpoint -Name "Root Endpoint" -Method "GET" -Endpoint "/"

# Test 3: Ingest Documents
Write-Host "Testing: Document Ingestion" -ForegroundColor Yellow
if (Test-Path "sample_documents\diabetes_management_en.txt") {
    try {
        $files = @(
            Get-Item "sample_documents\diabetes_management_en.txt"
            Get-Item "sample_documents\hypertension_guide_ja.txt"
        )

        $formData = @{}
        for ($i = 0; $i -lt $files.Count; $i++) {
            $formData["files"] = $files[$i]
        }

        $response = Invoke-RestMethod -Uri "$API_URL/ingest" `
            -Method Post `
            -Headers @{"X-API-Key" = $API_KEY} `
            -Form $formData

        Write-Host "✓ Success" -ForegroundColor Green
        $response | ConvertTo-Json -Depth 3
    }
    catch {
        Write-Host "✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}
else {
    Write-Host "✗ Sample documents not found" -ForegroundColor Red
}
Write-Host ""

# Wait for indexing
Start-Sleep -Seconds 2

# Test 4: Retrieve - English Query
$retrieveData = @{
    query = "What are the recommendations for Type 2 diabetes management?"
    top_k = 3
} | ConvertTo-Json

Test-Endpoint -Name "Retrieve (English)" -Method "POST" -Endpoint "/retrieve" -Data $retrieveData

# Test 5: Retrieve - Japanese Query
$retrieveDataJa = @{
    query = "高血圧の治療方法は？"
    top_k = 3
} | ConvertTo-Json

Test-Endpoint -Name "Retrieve (Japanese)" -Method "POST" -Endpoint "/retrieve" -Data $retrieveDataJa

# Test 6: Generate - English Query
$generateData = @{
    query = "How should I manage high blood pressure?"
    top_k = 3
} | ConvertTo-Json

Test-Endpoint -Name "Generate (English)" -Method "POST" -Endpoint "/generate" -Data $generateData

# Test 7: Generate - Japanese Query
$generateDataJa = @{
    query = "糖尿病の食事療法について教えてください"
    top_k = 3
} | ConvertTo-Json

Test-Endpoint -Name "Generate (Japanese)" -Method "POST" -Endpoint "/generate" -Data $generateDataJa

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Test Suite Complete" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
