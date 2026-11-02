#!/usr/bin/env bash
BASE=http://127.0.0.1:6099
files=$(grep -oE 'assets/[A-Za-z0-9_.-]+\.js' /tmp/idx.js | sort -u)
echo "chunks: $(echo "$files" | wc -l)"
for f in $files; do
  curl -s "$BASE/webui/$f" -o /tmp/x.js
  if grep -qE 'PasswordLogin|passwordLogin' /tmp/x.js; then
    echo "=== HIT $f ($(wc -c < /tmp/x.js) bytes)"
    grep -oE '.{80}(PasswordLogin|passwordLogin).{220}' /tmp/x.js | head -3
  fi
done
