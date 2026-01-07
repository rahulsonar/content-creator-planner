#!/bin/bash

echo "Testing Login API..."
echo ""

echo "Test 1: Successful login with correct credentials"
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "Admin123!"}' \
  | jq

echo ""
echo "---"
echo ""

echo "Test 2: Failed login with incorrect password"
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "wrongpassword"}' \
  | jq

echo ""
echo "---"
echo ""

echo "Test 3: Failed login with non-existent email"
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "nonexistent@example.com", "password": "Admin123!"}' \
  | jq
