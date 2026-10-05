"""
Minimal web HMI for the water tank (stand-in for ScadaBR in the Docker build).

Polls the PLC over Modbus/TCP (read-only for the process values) and lets the
operator open/close the outlet valve. Runs on http://<host>:8080
"""

import os
import threading
import time

from flask import Flask, jsonify, redirect, render_template_string
from pymodbus.client import ModbusTcpClient

PLC_HOST = os.environ.get("PLC_HOST", "127.0.0.1")
PLC_PORT = int(os.environ.get("PLC_PORT", "502"))
POLL_S = float(os.environ.get("POLL_S", "1.0"))

app = Flask(__name__)
state = {"level": None, "pump": None, "valve": None, "auto": None,
         "low_sp": None, "high_sp": None, "alarms": 0, "online": False,
         "updated": None}
lock = threading.Lock()
client = ModbusTcpClient(PLC_HOST, port=PLC_PORT, timeout=2)

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="2"><title>Water Tank HMI</title>
<style>
body{font-family:system-ui,sans-serif;background:#1d232a;color:#e6e6e6;margin:2rem}
.panel{display:flex;gap:2rem;align-items:flex-end}
.tank{width:140px;height:260px;border:3px solid #9aa;position:relative;background:#111}
.water{position:absolute;bottom:0;width:100%;background:#2f7fd8}
.sp{position:absolute;width:100%;border-top:2px dashed #fc0;font-size:.7rem}
table td{padding:.3rem 1rem}.on{color:#4c4}.off{color:#888}.alarm{color:#f44;font-weight:bold}
button{padding:.4rem 1rem;margin-top:1rem}
</style></head><body>
<h1>Water Treatment &mdash; Tank T-101</h1>
{% if not s.online %}<p class="alarm">COMMUNICATION LOST WITH PLC {{host}}</p>{% else %}
<div class="panel">
 <div class="tank">
  <div class="water" style="height:{{ s.level/10 }}%"></div>
  <div class="sp" style="bottom:{{ s.high_sp/10 }}%">HI {{ s.high_sp/10 }}%</div>
  <div class="sp" style="bottom:{{ s.low_sp/10 }}%">LO {{ s.low_sp/10 }}%</div>
 </div>
 <table>
  <tr><td>Tank level</td><td><b>{{ '%.1f' % (s.level/10) }} %</b></td></tr>
  <tr><td>Pump P-101</td><td class="{{ 'on' if s.pump else 'off' }}">{{ 'ON' if s.pump else 'OFF' }}</td></tr>
  <tr><td>Outlet valve V-101</td><td>{{ 'OPEN' if s.valve else 'CLOSED' }}</td></tr>
  <tr><td>Mode</td><td>{{ 'AUTO' if s.auto else 'MANUAL' }}</td></tr>
  <tr><td>Alarms</td><td class="{{ 'alarm' if s.alarms else '' }}">
   {% if s.hh %}HIGH-HIGH {% endif %}{% if s.ll %}LOW-LOW{% endif %}{% if not s.alarms %}none{% endif %}</td></tr>
 </table>
</div>
<form method="post" action="/valve/toggle"><button>Toggle outlet valve</button></form>
{% endif %}<p style="color:#777">PLC {{host}} &middot; last update {{ s.updated }}</p>
</body></html>"""


def poll() -> None:
    while True:
        try:
            if not client.connected:
                client.connect()
            hr = client.read_holding_registers(0, count=6)
            co = client.read_coils(0, count=3)
            if hr.isError() or co.isError():
                raise IOError("modbus error")
            with lock:
                state.update(level=hr.registers[0], low_sp=hr.registers[1],
                             high_sp=hr.registers[2], alarms=hr.registers[5],
                             pump=co.bits[0], valve=co.bits[1], auto=co.bits[2],
                             online=True, updated=time.strftime("%H:%M:%S"))
        except Exception:
            with lock:
                state["online"] = False
            client.close()
        time.sleep(POLL_S)


@app.get("/")
def index():
    with lock:
        s = type("S", (), dict(state, hh=state["alarms"] & 1,
                                ll=state["alarms"] & 2))
    return render_template_string(PAGE, s=s, host=f"{PLC_HOST}:{PLC_PORT}")


@app.get("/api/state")
def api_state():
    with lock:
        return jsonify(state)


@app.post("/valve/toggle")
def toggle_valve():
    with lock:
        current = state["valve"]
    if current is not None:
        client.write_coil(1, not current)
    return redirect("/")


if __name__ == "__main__":
    threading.Thread(target=poll, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
