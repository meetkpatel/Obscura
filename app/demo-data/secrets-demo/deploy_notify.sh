#!/bin/bash
# Planted DEMO secret (fake bearer token) — posts deploy status to an API.
AUTH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJERU1PLXVzZXIiLCJkZW1vIjp0cnVlfQ.DEMOfakesignatureNOTAREALtoken00"
curl -s -H "Authorization: Bearer $AUTH_TOKEN" https://api.example/deploy/notify
