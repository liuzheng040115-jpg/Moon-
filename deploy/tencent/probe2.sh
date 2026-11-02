#!/usr/bin/env bash
# 摸 NapCat WebUI 的登录接口
TOKEN=297a8d1981da
BASE=http://127.0.0.1:6099

echo "== webui html =="
curl -s "$BASE/" | head -30

JS=$(curl -s "$BASE/" | grep -oE '/assets/[^"]+\.js' | head -1)
echo "== js bundle: $JS =="
if [ -n "$JS" ]; then
  curl -s "$BASE$JS" | grep -oE '"/api/[A-Za-z0-9_/.-]+"' | sort -u | head -80
  echo "== login 相关 =="
  curl -s "$BASE$JS" | grep -oiE '"[A-Za-z0-9_/-]*(login|password|quick)[A-Za-z0-9_/-]*"' | sort -u | head -40
fi

echo "== napcat cli =="
command -v napcat || true
napcat --help 2>&1 | head -40 || true
