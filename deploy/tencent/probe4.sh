#!/usr/bin/env bash
BASE=http://127.0.0.1:6099
echo "== webui html =="
curl -s "$BASE/webui/" | head -c 1500
echo
JS=$(curl -s "$BASE/webui/" | grep -oE '/webui/[^"]+\.js|/assets/[^"]+\.js' | head -3)
echo "== js: $JS =="
for j in $JS; do
  echo "--- $j ---"
  curl -s "$BASE$j" | grep -oE '"/api/[A-Za-z0-9_/.-]+"' | sort -u | head -60
  echo "--- login words ---"
  curl -s "$BASE$j" | grep -oiE '"/api/[A-Za-z0-9_/.-]*(login|password|quick|account)[A-Za-z0-9_/.-]*"' | sort -u | head -30
done
