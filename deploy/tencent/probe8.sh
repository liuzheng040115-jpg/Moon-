#!/usr/bin/env bash
echo "== QQLogin endpoints in main bundle =="
grep -oE 'QQLogin/[A-Za-z0-9_]+' /tmp/idx.js | sort -u
echo "== passwordLogin def =="
grep -oE '.{120}passwordLogin.{200}' /tmp/idx.js | head -3
echo "== GetQuickLoginList def =="
grep -oE '.{100}QuickLoginList.{150}' /tmp/idx.js | head -3
