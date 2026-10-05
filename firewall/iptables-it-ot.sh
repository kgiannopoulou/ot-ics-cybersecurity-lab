#!/bin/sh
# IT <-> OT conduit policy for the Docker build (mirrors firewall/rules.md).
# Default deny; only explicitly listed flows cross the zone boundary.
set -e
IT=10.10.10.0/24
OT=10.30.30.0/24
ENG_WS=10.10.10.50      # authorised engineering workstation
HMI=10.30.30.20
WAZUH=10.10.10.100

iptables -F FORWARD
iptables -P FORWARD DROP

# Stateful return traffic
iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Engineering workstation -> HMI web UI only (no direct PLC access from IT)
iptables -A FORWARD -s $ENG_WS -d $HMI -p tcp --dport 8080 -j ACCEPT

# OT hosts -> Wazuh manager (agent events + enrollment), outbound only
iptables -A FORWARD -s $OT -d $WAZUH -p tcp -m multiport --dports 1514,1515 -j ACCEPT

# Explicitly log and drop any IT host attempting Modbus into OT
iptables -A FORWARD -s $IT -d $OT -p tcp --dport 502 -j LOG --log-prefix "FW-DENY-MODBUS-IT2OT: "
iptables -A FORWARD -s $IT -d $OT -p tcp --dport 502 -j DROP

# Everything else: log, then the default policy drops it
iptables -A FORWARD -j LOG --log-prefix "FW-DENY: "
echo "IT/OT conduit policy loaded"
