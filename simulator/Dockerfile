FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY simulator/water_tank_plc.py .
EXPOSE 502
CMD ["python", "water_tank_plc.py", "--port", "502"]
