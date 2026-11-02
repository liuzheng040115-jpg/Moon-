#!/usr/bin/env bash
TOKEN=297a8d1981da
echo "== listen =="
ss -ltnp 2>/dev/null | grep -E '6099|3001|8080' || echo "no 6099/3001/8080"
echo "== log tail =="
tail -c 1200 /root/napcat.log
echo
echo "== / =="
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' http://127.0.0.1:6099/
echo "== /webui/ =="
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' http://127.0.0.1:6099/webui/
echo "== /api/Base/ =="
curl -s -H "Authorization: Bearer $TOKEN" -o /dev/null -w '%{http_code} %{size_download}\n' http://127.0.0.1:6099/api/Base/
echo "== body of / =="
curl -s http://127.0.0.1:6099/ | head -c 600
