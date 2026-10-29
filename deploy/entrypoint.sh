#!/bin/sh
# Starts $ATF_APP in browser mode on $PORT, open to other computers (the container is the boundary).
set -e
export ATF_UI_WEB="${PORT:-8080}"
export ATF_UI_WEB_HOST="${ATF_UI_WEB_HOST:-0.0.0.0}"
exec xvfb-run -a wine bin/atf.exe run "$ATF_APP"
