# Water tank PLC program

`water_tank.st` is the IEC 61131-3 Structured Text program loaded into **OpenPLC Runtime** in the VM build of the lab.

| Behaviour | Logic |
|---|---|
| Fill | level < low setpoint (30 %) → pump ON |
| Stop | level > high setpoint (80 %) → pump OFF |
| Safety interlock | level ≥ 95 % → pump forced OFF in *any* mode |
| Setpoint sanity | low SP must be 10–50 %, high SP 60–90 %, else reset to default |
| Alarms | bit0 HIGH-HIGH (≥95 %), bit1 LOW-LOW (≤5 %) |

The interlock and setpoint range checks are deliberate **defence-in-depth inside the controller**: even if an unauthorised Modbus write reaches the PLC, it can't push the process outside its safe envelope. That's the "last line of defence" control from the threat model.

## Loading into OpenPLC
1. OpenPLC web UI (`http://10.30.30.10:8080`) → **Programs → Upload Program** → `water_tank.st`.
2. **Slave Devices**: optionally add the process simulator as a Modbus slave so it feeds `%IW100`.
3. **Settings**: enable Modbus server on port 502 and disable DNP3/EtherNet/IP (they aren't used, so they're attack surface).
4. Change the default `openplc/openplc` credentials before connecting the PLC to any network.

In the Docker build, `simulator/water_tank_plc.py` runs the same logic so the lab works without OpenPLC.
