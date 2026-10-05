(*
  Water Tank T-101 level control - IEC 61131-3 Structured Text
  Target: OpenPLC Runtime (Modbus/TCP slave on port 502)

  Located variables map 1:1 onto the Modbus table used by the HMI:
    %QX100.0  coil 0  pump_running
    %QX100.1  coil 1  valve_open
    %QX100.2  coil 2  auto_mode
    %QX100.3  coil 3  manual_pump_cmd
    %IW100    input register 0  tank_level from the process simulator (0-1000)
    %MW0      holding reg 1024  low_setpoint   (OpenPLC maps %MW0 -> HR 1024)
    %MW1      holding reg 1025  high_setpoint
    %MW2      holding reg 1026  alarm_word

  When the level comes from a real/simulated transmitter, wire it to %IW100.
*)
PROGRAM water_tank
  VAR
    pump_running    AT %QX100.0 : BOOL := FALSE;
    valve_open      AT %QX100.1 : BOOL := TRUE;
    auto_mode       AT %QX100.2 : BOOL := TRUE;
    manual_pump_cmd AT %QX100.3 : BOOL := FALSE;
    tank_level      AT %IW100   : INT;
    low_setpoint    AT %MW0     : INT := 300;
    high_setpoint   AT %MW1     : INT := 800;
    alarm_word      AT %MW2     : INT := 0;
  END_VAR
  VAR CONSTANT
    HH_LIMIT : INT := 950;   (* 95.0 % high-high trip *)
    LL_LIMIT : INT := 50;    (*  5.0 % low-low alarm  *)
  END_VAR

  (* Setpoint sanity: reject values outside the engineering range.
     A tampered setpoint must never be able to disable the hysteresis. *)
  IF (low_setpoint < 100) OR (low_setpoint > 500) THEN
    low_setpoint := 300;
  END_IF;
  IF (high_setpoint < 600) OR (high_setpoint > 900) THEN
    high_setpoint := 800;
  END_IF;

  (* Hysteresis control *)
  IF auto_mode THEN
    IF tank_level < low_setpoint THEN
      pump_running := TRUE;
    ELSIF tank_level > high_setpoint THEN
      pump_running := FALSE;
    END_IF;
  ELSE
    pump_running := manual_pump_cmd;
  END_IF;

  (* Safety interlock - overrides auto AND manual mode *)
  IF tank_level >= HH_LIMIT THEN
    pump_running := FALSE;
  END_IF;

  (* Alarms *)
  alarm_word := 0;
  IF tank_level >= HH_LIMIT THEN
    alarm_word := alarm_word OR 1;
  END_IF;
  IF tank_level <= LL_LIMIT THEN
    alarm_word := alarm_word OR 2;
  END_IF;
END_PROGRAM

CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK MainTask(INTERVAL := T#100ms, PRIORITY := 0);
    PROGRAM Inst0 WITH MainTask : water_tank;
  END_RESOURCE
END_CONFIGURATION
