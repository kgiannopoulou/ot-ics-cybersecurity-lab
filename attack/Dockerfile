# Red-team container: an unauthorised workstation on the OT network.
# Runs the lab attack scripts from 10.30.30.66 against the PLC. Started only
# under the "redteam" compose profile (or by tools/validate.py), never by
# default, and only ever targets this lab's own PLC.
FROM python:3.12-slim
WORKDIR /opt/lab
RUN pip install --no-cache-dir "pymodbus==3.9.2"
COPY attack ./attack
# Idle until told to run a scenario (docker compose run / exec).
CMD ["sleep", "infinity"]
