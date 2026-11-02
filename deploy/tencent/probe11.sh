#!/usr/bin/env bash
BASE=http://127.0.0.1:6099
TOKEN=297a8d1981da
MD5=$(printf '%s' 'qhs644602' | md5sum | cut -d' ' -f1)

echo "== auth/login =="
RESP=$(curl -s -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' -d "{\"token\":\"$TOKEN\"}")
echo "$RESP"
JWT=$(printf '%s' "$RESP" | grep -oE '"token":"[^"]+"' | head -1 | cut -d'"' -f4)
echo "jwt=${JWT:0:40}..."

if [ -n "$JWT" ]; then
  echo "== password login =="
  curl -s -X POST "$BASE/api/QQLogin/PasswordLogin" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $JWT" \
    -d "{\"uin\":\"3680764546\",\"passwordMd5\":\"$MD5\"}"
  echo
fi
