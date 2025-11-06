#!/bin/bash
# API Testing Script for Healthcare RAG Assistant

API_URL="http://localhost:8000"
API_KEY="${API_KEY:-dev-key-change-in-production}"

echo "==================================="
echo "Healthcare RAG API Test Script"
echo "==================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test endpoint
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4

    echo -e "${YELLOW}Testing: $name${NC}"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$API_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "X-API-Key: $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$endpoint")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Success (HTTP $http_code)${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
        echo "$body"
    fi
    echo ""
}

# Test 1: Health Check
test_endpoint "Health Check" "GET" "/health" ""

# Test 2: Root Endpoint
test_endpoint "Root Endpoint" "GET" "/" ""

# Test 3: Ingest Documents
echo -e "${YELLOW}Testing: Document Ingestion${NC}"
if [ -f "sample_documents/diabetes_management_en.txt" ]; then
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "X-API-Key: $API_KEY" \
        -F "files=@sample_documents/diabetes_management_en.txt" \
        -F "files=@sample_documents/hypertension_guide_ja.txt" \
        "$API_URL/ingest")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Success (HTTP $http_code)${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
        echo "$body"
    fi
else
    echo -e "${RED}✗ Sample documents not found${NC}"
fi
echo ""

# Wait a moment for indexing
sleep 2

# Test 4: Retrieve - English Query
test_endpoint "Retrieve (English)" "POST" "/retrieve" '{
    "query": "What are the recommendations for Type 2 diabetes management?",
    "top_k": 3
}'

# Test 5: Retrieve - Japanese Query
test_endpoint "Retrieve (Japanese)" "POST" "/retrieve" '{
    "query": "高血圧の治療方法は？",
    "top_k": 3
}'

# Test 6: Retrieve with Translation
test_endpoint "Retrieve with Translation (EN->JA)" "POST" "/retrieve" '{
    "query": "diabetes treatment guidelines",
    "top_k": 2,
    "output_language": "ja"
}'

# Test 7: Generate - English Query
test_endpoint "Generate (English)" "POST" "/generate" '{
    "query": "How should I manage high blood pressure?",
    "top_k": 3
}'

# Test 8: Generate - Japanese Query
test_endpoint "Generate (Japanese)" "POST" "/generate" '{
    "query": "糖尿病の食事療法について教えてください",
    "top_k": 3
}'

echo "==================================="
echo "Test Suite Complete"
echo "==================================="
