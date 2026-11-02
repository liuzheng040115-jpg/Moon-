#!/usr/bin/env bash
BASE=http://127.0.0.1:6099
for f in $(grep -oE 'assets/[A-Za-z0-9_.-]+\.js' /tmp/idx.js | sort -u); do
  curl -s "$BASE/webui/$f" -o /tmp/x.js
  if grep -q 'auth/login' /tmp/x.js; then
    echo "=== $f"
    grep -oE '.{140}auth/login.{240}' /tmp/x.js | head -2
  fi
done
