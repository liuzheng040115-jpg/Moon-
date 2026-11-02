#!/usr/bin/env bash
BASE=http://127.0.0.1:6099
grep -oE 'assets/(qq_login|web_login)[A-Za-z0-9_.-]*\.js' /tmp/idx.js | sort -u
echo "== try chunks =="
for f in $(grep -oE 'assets/(qq_login|web_login)[A-Za-z0-9_.-]*\.js' /tmp/idx.js | sort -u); do
  echo "--- $f ---"
  curl -s "$BASE/webui/$f" -o /tmp/chunk.js
  wc -c < /tmp/chunk.js
  grep -oE '"/[A-Za-z0-9_/.-]+"' /tmp/chunk.js | sort -u | head -40
  echo "  .. password words .."
  grep -oiE '[A-Za-z0-9_/-]*(password|pwd|quicklogin)[A-Za-z0-9_/-]*' /tmp/chunk.js | sort -u | head -20
done
