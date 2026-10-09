# Reference: dump structure & Vaillant eBUS patterns

This table is built from evidence-backed analysis of community dumps (issues #99/#102/#109/#111 and the GOLDEN fixtures). Item sources: dump sections and `custom_components/vaillant_ebus/coordinator.py` (`_define_custom_registers`).

## Discovery dump (v4) structure

| section | content |
|---|---|
| `metadata` | timestamp, ebusd_version, register_count, grab_duration, dump_version=4, integration_version, ebusd_info, ebusd_configuration (addon options usually `available: false`) |
| `raw_find_lines` | raw `find` output (`circuit Name = value`), incl. `no data stored` / `(ERR: ...)` |
| `raw_find_lines_after` | effective state after the runtime `define` pass (optional) — use `after=True` for effective runtime tests |
| `before_registers` / `after_registers` | normalized: circuit, name, value, writable, has_data, from_map, disabled; all discovered + fallback probes |
| `grab` | raw bus telegram lines (`... / 09410111... = 3`) |
| `unknown_telegrams` / `labeled_telegrams` | traffic derived by `backend/grab_parser.py`: master, slave, message, sub, bytes, count |

Sentinels (unavailable, not a normal value): `no data stored`, `(empty ...)`, `(ERR: element not found)`, `(ERR: invalid position ...)`, `-`, and NaN payloads such as `0x7fffffff`.

## B524 / ctlv* register addressing

B524 is the CTLV2/CTLV3 controller message. Sub-address pattern: read `0602 00 <zone> <reg> 00`, write `0702 01 <zone> <reg> 00`. Known reg-ids:

| reg-id | register | remark |
|---|---|---|
| `0004` | HwcTempDesired | |
| `0005` | HwcStorageTemp | tempv, 2-byte; NaN sentinel when there is no tank (boiler detection, strong assumption) |
| `0009` / `000a` | HwcHolidayStartPeriod / HwcHolidayEndPeriod | HDA:3 date; reset 01.01.2015/01.01.2019 |
| `000d` | HwcSFMode | myVaillant "Hwc Load" backend (upstream #568) |
| `000f` | HwcStatus (zonestatus2) | auto=0, load=9, off=10 |
| `00da`/`00db` | ManualCoolingStartDate / ManualCoolingEndDate | runtime define, HDA:3 |
| `0028` (z1) | z1RoomHumidity | `IGN:4 ... EXP` |
| `0020..0025` | Hc1/Hc2 FlowTempCalc..PumpStarts | EXP/ULG, runtime define |

Runtime define format: `r5,ctlv2,<name>,<label>,31,15,B524,<read-sub>,value,,IGN:4,,,,value,,<type>,` and a separate `w,ctlv2,<name>,...,0201<...>,value,m,HDA:3` for writes.

## Message-write conventions

- **B509 (BAI/boiler)**: read request prefix `0d`, write prefix `0e`. `0dF203`/`0dF303` read, `0eF203`/`0eF303` write. This is the upstream product-specific include convention.
- **The `onoff` field type is NOT available in runtime define scope** (the template lives in `vaillant/_templates.csv`, not in the global scope). Use `UCH,0=off;1=on`.
- **B510 SetMode**: semicolon fields; `releaseCooling` is **index 9** (0-based after `hcmode;flowtempdesired;...`). `find -v` does not show write-only registers — use `find -w` or the define itself.
- **Write verification**: ebusd `read` answers from a cache that the write itself fills → a cached read-back always "verifies". A forced `read -f` (and a retry) is the only real check.

## Status fields (B511)

| circuit field | layout | values |
|---|---|---|
| `Status01.pumpstate` | field 6 | `0=off 1=on 2=overrun 4=hwc` → **DHW-active signal** on units without Status00/07 |
| `Status00` | multi-field | supplytemp, waterpressure, compressormodulation, compressorstate, heatingstate, field6, defrost, compressorpower |
| `Status07` | heatermain bits | `b3_heating`, `b4_cooling`, `b7_warmwater` (and `display_b5_noisereduction` on HW5103) |

Energy Manager State derivation: `RunDataStatuscode` → otherwise `Status00`/`Status07` bits → otherwise `SetMode.releaseCooling` (Cooling) / `Status01.pumpstate==hwc` (DHW). An explicit shutdown/standby/compressor-off always wins.

## Circuit resolution

- `15.ctlv3.tsp` is a **symlink to `15.ctlv2.tsp`** (upstream PR #266): ebusd can name the same controller `ctlv2` or `ctlv3`. Use the SCAN identity (`scan.15` line in metadata/raw) and the graph owner resolution (`resolve_register_circuit`), never the circuit name as truth.
- An exact node (e.g. bare `ctlv2`) is authoritative only if it is the owner of the control/DHW registers. Logical sub-devices (dhw node) aggregate registers from multiple source circuits — resolve the owner per register via the source circuit.
- Duplicate find lines (one live, one `no data stored`) = duplicate elements in the loaded CSV; check which element a write resolves (`ebusctl elements`).

## Runtime define rules

- Definitions are volatile: re-inject on every connect in `_define_custom_registers()`; only changed/failed ones are resent.
- Additive: absent/`ERR` → register stays unavailable without a normal entity; no active polling that changes bus behavior.
- Community data → fixture-backed test (decoded value and absent path); classification confirmed / strong assumption / speculative / discovery-only in the analysis note.

## Useful B509/B511/B51A/B516 definitions (from coordinator, evidence-backed)

- HMUX0 `Status00`: `r,hmu,Status00,...,31,8,B511,00,<fields incl. compressorstate UCH 0=off;4=heating;24=hot_water;110=defrosting,...>`
- HMUX0 `RunDataElPowerConsumption`: `r,hmu,...,31,8,B509,055402005b0d,value,,IGN:4,,,,value,,EXP,,W,` (upstream #522)
- `SourceTempInput`: `r,hmu,...,31,8,B51A,05ff3222,value,,IGN:3,,,,value,,D2C,,°C,` (upstream PR #565; air/water gives a 3-byte stub → unavailable)
- B516 cooling energy: `CoolEnvYieldTotal` `1000ffff02050000`, `CoolElecConsTotal` `1000ffff03050000`, and day/month variants with `b516_date_bytes` (upstream #490/#600)

## Data dump vs loose commands

For "does a write not work?" / "which telegram does the controller accept?" the **export_discovery_dump with a grab** is the easiest, strongest step: the passive grab catches both write telegrams (integration and app), and `before/after_registers` show the read-back. Ask the user: run `export_discovery_dump` with `grab_duration: 30` and perform the action (HA write or app write) while the grab runs; compare both dumps → write-vs-app transactions.
