#!/usr/bin/env bash
# ElCaciqueDeck - CaciqueGuía setup (local AI helper)
#   bash ~/elcaciquedeck/guide/setup-guide.sh            (picks a model that fits this computer's memory)
#   CQ_MODEL=qwen2.5:7b bash ~/elcaciquedeck/guide/setup-guide.sh   (choose one yourself)
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/guide"
start_report "guide-setup"
step "1/4  Checks"
need_docker
RAM="$(total_ram_gb)"
if [ -n "$CQ_MODEL" ]; then MODEL="$CQ_MODEL"
elif awk "BEGIN{exit !($RAM >= 30)}"; then MODEL="qwen2.5:14b"
elif awk "BEGIN{exit !($RAM >= 14)}"; then MODEL="qwen2.5:7b"
else MODEL="qwen2.5:3b"; fi
ok "Memory ${RAM} GB -> AI model: $MODEL"
awk "BEGIN{exit !($RAM < 7)}" && warn "Less than 7 GB of memory: CaciqueGuía will be slow"
step "2/4  Settings"
mkdir -p "$DATA/ollama"
printf '# CaciqueGuía settings - stays on this laptop\nOLLAMA_DIR=%s\nGUIDE_MODEL=%s\n' "$DATA/ollama" "$MODEL" > "$DIR/.env"
open_port 8070 "CaciqueGuía"
step "3/4  Downloading the AI engine and starting it"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet and run this again."
docker compose up -d || fail "Could not start the AI engine."
wait_for "http://127.0.0.1:11434" 60 || fail "The AI engine did not start"
ok "AI engine running"
step "4/4  Downloading the AI model (one time; 2-9 GB depending on the model - be patient)"
docker exec caciqueguide-ai ollama pull "$MODEL" && ok "Model $MODEL ready" || fail "Could not download $MODEL"
mkdir -p "$REPO/reports/run"; pkill -f "[c]aciqueguia.py" 2>/dev/null
nohup python3 "$DIR/caciqueguia.py" >"$REPO/reports/run/guide.log" 2>&1 &
ok "CaciqueGuía started: http://$(laptop_ip):8070"
finish
