#!/usr/bin/env bash
BASE=http://127.0.0.1:6099
JS=/webui/assets/index-Bhl_Ql1g.js
curl -s "$BASE$JS" > /tmp/idx.js
echo "== size =="; wc -c < /tmp/idx.js
echo "== any Login tokens =="
grep -oE '[A-Za-z0-9_/.]*[Ll]ogin[A-Za-z0-9_/.]*' /tmp/idx.js | sort -u | head -40
echo "== api/ patterns =="
grep -oE '["`]/?(api|API)/[A-Za-z0-9_/.-]+' /tmp/idx.js | sort -u | head -50
echo "== fetch calls =="
grep -oE '(fetch|axios)\([^)]{0,80}' /tmp/idx.js | head -20
