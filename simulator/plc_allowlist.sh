#!/bin/sh
# Host-based Modbus allow-list for the PLC container (mitigation for F-01).
#
# The network IDS detects an unauthorised Modbus client but does not stop it:
# the PLC still serves the request. This script enforces, on the controller
# itself, that only the HMI may reach TCP 502 — the control a real deployment
# would place at the switch (802.1X / port security) or on the PLC host.
#
#   docker compose exec plc /allowlist.sh on     # apply (only the HMI may talk Modbus)
#   docker compose exec plc /allowlist.sh off     # remove (back to the vulnerable baseline)
#   docker compose exec plc /allowlist.sh status
#
# tools/validate.py toggles this to prove the attack succeeds before and is
# blocked after the mitigation. Requires NET_ADMIN on the plc service.
set -e

HMI="${PLC_ALLOWED_CLIENT:-10.30.30.20}"
PORT="${PLC_PORT:-502}"
CHAIN=INPUT

ensure_tools() {
    command -v iptables >/dev/null 2>&1 || apk add --no-cache iptables >/dev/null 2>&1
}

clear_rules() {
    # Remove any lab rules (repeat until the delete fails: handles duplicates).
    while iptables -D $CHAIN -p tcp --dport "$PORT" -s "$HMI" -j ACCEPT 2>/dev/null; do :; done
    while iptables -D $CHAIN -p tcp --dport "$PORT" -j LOG --log-prefix "PLC-DENY-MODBUS: " 2>/dev/null; do :; done
    while iptables -D $CHAIN -p tcp --dport "$PORT" -j DROP 2>/dev/null; do :; done
}

case "$1" in
  on)
    ensure_tools
    clear_rules  # idempotent: start clean so repeated "on" doesn't stack rules
    iptables -A $CHAIN -p tcp --dport "$PORT" -s "$HMI" -j ACCEPT
    iptables -A $CHAIN -p tcp --dport "$PORT" -j LOG --log-prefix "PLC-DENY-MODBUS: "
    iptables -A $CHAIN -p tcp --dport "$PORT" -j DROP
    echo "allow-list ON: only $HMI may reach $PORT/tcp"
    ;;
  off)
    ensure_tools
    clear_rules
    echo "allow-list OFF: $PORT/tcp open to the OT subnet (vulnerable baseline)"
    ;;
  status)
    ensure_tools
    iptables -L $CHAIN -n --line-numbers | grep -E "dpt:$PORT|Chain INPUT" || echo "no lab rules"
    ;;
  *)
    echo "usage: $0 {on|off|status}" >&2
    exit 2
    ;;
esac
