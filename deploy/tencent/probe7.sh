#!/usr/bin/env bash
BASE=http://127.0.0.1:6099
curl -s "$BASE/webui/assets/qq_login-Cu4Sqvn4.js" -o /tmp/qq.js
echo "== QQLogin refs =="
grep -oE '.{60}QQLogin[A-Za-z0-9_/.-]*.{60}' /tmp/qq.js | head -20
echo "== passwordLogin ctx =="
grep -oE '.{150}passwordLogin.{250}' /tmp/qq.js | head -4
echo "== common api helper =="
grep -oE '.{80}"/api".{120}' /tmp/qq.js | head -4
