FROM python:3.12-slim
WORKDIR /app
# iptables lets the container enforce the host Modbus allow-list (F-01
# mitigation, simulator/plc_allowlist.sh); harmless when the allow-list is off.
RUN apt-get update && apt-get install -y --no-install-recommends iptables \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY simulator/water_tank_plc.py .
COPY simulator/plc_allowlist.sh /allowlist.sh
RUN chmod +x /allowlist.sh
EXPOSE 502
CMD ["python", "water_tank_plc.py", "--port", "502"]
