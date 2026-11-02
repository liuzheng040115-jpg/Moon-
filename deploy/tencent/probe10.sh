#!/usr/bin/env bash
BASE=http://127.0.0.1:6099
TOKEN=297a8d1981da
MD5=$(printf '%s' 'qhs644602' | md5sum | cut -d' ' -f1)
echo "md5=$MD5"
echo "== with token =="
curl -s -X POST "$BASE/api/QQLogin/PasswordLogin" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"uin\":\"3680764546\",\"passwordMd5\":\"$MD5\"}"
echo
echo "== without token =="
curl -s -X POST "$BASE/api/QQLogin/PasswordLogin" \
  -H 'Content-Type: application/json' \
  -d "{\"uin\":\"3680764546\",\"passwordMd5\":\"$MD5\"}"
echo
echo "== log tail =="
tail -c 800 /root/napcat.log
