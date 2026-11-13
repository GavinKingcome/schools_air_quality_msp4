# How it works

*A one-page picture of how the Early Years & School Pollution Monitor gets from sensor readings to the figures in a school's popup. Written 12 November 2026.*

## The big picture

```
  SENSOR NETWORKS                 THE DATABASE                    THE MAP
  (LAQN, Breathe, AQE)

        │  fetch_all_readings
        │  every hour at :00
        ▼
                              ┌──────────────────┐
                              │  Reading table   │  one row per sensor per hour
                              └──────────────────┘
                                      │
                                      │  assign_sensors
                                      │  every hour at :10
                                      ▼
                              ┌──────────────────┐
                              │  School table    │  each school's direct sensor,
                              │                  │  spare sensor, distances,
                              └──────────────────┘  data source
                                      │
                                      │  get_current_reading
                                      │  each time the map opens
                                      ▼
                                                            ┌──────────────┐
                              LAEI 2022 value at the school │ School popup │
                              × the sensor's ratio      ───▶│  figures +   │
                              (or the direct reading)       │  confidence  │
                                                            └──────────────┘

  Once a year (or when needed):
  fetch_annual_stats / fetch_breathe_annual_stats ──▶ SensorAnnualStats table
  (the annual averages that the ratio divides by)
```

There are three jobs, and each feeds the next:

1. **Fetch** collects sensor readings. It knows nothing about schools.
2. **Assign** decides which sensor each school uses. It doesn't fetch anything.
3. **The map** puts them together when someone opens it.

## 1. Where the data comes from

| Source | What it gives | Where it's stored |
|---|---|---|
| **LAEI 2022** (London Atmospheric Emissions Inventory) | Modelled annual averages of NO₂, NOx, PM2.5 and PM10 on a 20 m grid. Fixed: the same value every day. | On each school and childcare setting (`no2_2022`, `pm25_2022`, `pm10_mean_2022` and so on) |
| **LAQN** (London Air Quality Network, run by Imperial College) | Hourly readings from reference-grade monitors | `Sensor` and `Reading` tables |
| **AQE** (Air Quality England, run by Ricardo, now part of WSP) | Hourly readings from reference-grade monitors. Southwark moved four sites here in March 2025. The site has been offline since October 2026. | `Sensor` and `Reading` tables |
| **Breathe London** (run by a Vodafone-led group since 2025) | Hourly readings from low-cost, calibrated sensors. NO₂ and PM2.5 only. | `Sensor` and `Reading` tables |
| **GIAS** (Get Information About Schools) and **Ofsted** | School and childcare locations and details, prepared by `build_slice.py` in the analysis repo | `School` and `ChildcareSetting` tables |

**Reference grade** means the monitor is the official standard instrument, checked and recalibrated regularly. LAQN and AQE are reference grade. Breathe London is not, but its data is calibrated against reference monitors.

## 2. Keeping the sensor list up to date

The **sync** commands copy each network's list of sensors into the `Sensor` table: name, location, network, site type, and whether it's active.

| Command | Network |
|---|---|
| `sync_laqn_sensors` | LAQN |
| `sync_breathe_sensors` | Breathe London (keeps only each site's current installation) |
| `sync_aqe_sensors` | AQE (also links each old LAQN code to its new AQE code) |

These are run by hand, when sensors may have changed.

**Site type** comes from each network's own label: urban background, roadside, kerbside (saved as roadside), suburban or industrial. It matters because only **urban background** sensors can be used directly for a school.

## 3. Fetch: collecting the readings

`fetch_all_readings` runs **every hour at :00** (from cron on the Mac). It runs three commands in turn:

1. `fetch_laqn_readings`
2. `fetch_breathe_readings`
3. `fetch_aqe_readings` (skipped while AQE has no sensors in the database)

Each run looks back **48 hours**. Readings already in the database are left alone, so the overlap only adds readings that arrived late (some sites publish in batches) or hours missed while the Mac was asleep.

## 4. Annual averages

The adjusted method divides a sensor's current reading by its **annual average**, so each sensor needs one. They live in the `SensorAnnualStats` table.

| Command | Networks | Period |
|---|---|---|
| `fetch_annual_stats` | LAQN, AQE | A calendar year (default: last year) |
| `fetch_breathe_annual_stats` | Breathe London | The last 12 full months, saved with the real dates in `period_start` and `period_end` |

An average only counts if at least **75%** of the hours had a value (the usual UK rule). Breathe uses the last 12 months because its new devices only started in spring 2025, and old and new devices must not be mixed.

## 5. Assign: which sensor each school uses

`assign_sensors` runs **every hour at :10**, after the fetch. For each school it decides:

**Which sensors count at all.** Only sensors that are active **and** have sent a reading in the **last 7 days**. (A site can be officially open but silent, like LB5.)

**A direct sensor.** An **urban background** sensor within **150 m**, from any network. Roadside sensors don't count, because they mostly measure their own road.

**A spare sensor** (saved as `reference_sensor`):

1. the nearest **reference** sensor (LAQN or AQE) within **2 km** that has an annual average, or if there isn't one,
2. the nearest **Breathe London** sensor within **2 km** that has a 12-month average.

The spare is never the school's own direct sensor, since it would go quiet at the same time.

**The data source:**

| Has a direct sensor? | Has a spare? | Data source |
|---|---|---|
| Yes | either | `DIRECT` |
| No | Yes | `ADJUSTED` |
| No | No | `LAEI` (LAEI only) |

Because reference sensors come first, schools switch back to a reference sensor on their own when one returns (for example, when AQE comes back online).

`--dry-run` shows what would change without saving anything.

## 6. The figure on the map

Each time the map opens, `get_current_reading` (in `schools/models.py`) works out each school's figures. It tries three methods in order and stops at the first that works.

| Method | When | Figure | Confidence |
|---|---|---|---|
| **1. Direct** | The direct sensor's latest reading is no more than **48 hours** old | The sensor's own reading | High (reference) or Medium-high (Breathe) |
| **2. Adjusted** | The spare sensor has a recent reading and an annual average | LAEI 2022 value × (sensor now ÷ sensor's annual average) | Medium (reference) or Medium-low (Breathe) |
| **3. LAEI only** | Neither of the above | The LAEI 2022 value | Low |

Some details:

- The ratio is capped between **0.2 and 5**, so one faulty reading can't produce an extreme figure.
- If the sensor has no factor for a pollutant (Breathe has no PM10), that pollutant is shown as the LAEI 2022 value, with an **"LAEI Baseline"** badge.
- A direct school whose sensor goes quiet falls back to Method 2 with its spare, then to Method 3.

**Why the ratio works over a distance**, and why site type matters more than distance, is explained in `docs/SENSOR_DISTANCE.md`.

## 7. What the school popup shows

- **Data source:** sensor at the school, LAEI 2022 × reference (or Breathe London) sensor adjustment, or LAEI 2022 modelled annual average.
- **The sensor:** its code, network, "(low-cost, calibrated)" for Breathe, site type, and distance.
- **Confidence:** from the table above.
- **Each pollutant:** the figure, a "Live" or "LAEI Baseline" badge where it applies, and how it compares with the WHO, EU and UK limits.
- **When the sensor last reported**, and a note if that was outside school hours.

Childcare popups show LAEI 2022 values only.

## 8. What happens when things change

| Change | What happens |
|---|---|
| A sensor misses a few hours | The next hourly fetch collects them (48-hour look-back). |
| A sensor is quiet for more than 48 hours | Its schools fall back to their spare, or to LAEI only, when the map opens. |
| A sensor is quiet for more than 7 days | The next `assign_sensors` run stops using it, and its schools are reassigned. |
| It starts reporting again | The next fetch collects its readings, and the next `assign_sensors` run uses it again. |
| A new sensor is installed | Run `sync_breathe_sensors` (or the LAQN or AQE sync). Once it reports, it can be a **direct** sensor straight away. It can only be a **spare** once it has a 12-month (or calendar-year) average. |
| AQE comes back online | Run `sync_aqe_sensors`, fetch its readings and history, then `fetch_annual_stats`. Schools near the AQE sites switch from Breathe to AQE on the next `assign_sensors` run. |

## 9. The schedule (on the Mac)

`mycron.txt` holds two lines. Install them with `crontab mycron.txt`, and check with `crontab -l`.

| When | What | Log heading |
|---|---|---|
| Every hour at :00 | `fetch_all_readings --hours=48` | `=== <date>` |
| Every hour at :10 | `assign_sensors` | `=== assign <date>` |

Both write to `/tmp/sensor_fetch.log`. cron skips any hour when the Mac is asleep; the 48-hour look-back fills the gap at the next run.

The live server will need its own schedule, independent of the Mac (see the roadmap).

## 10. Where things live

| What | File |
|---|---|
| Sensor, Reading, SensorAnnualStats models | `air_quality/models.py` |
| Network API code | `air_quality/services/laqn_api.py`, `breathe_london_api.py`, `aqe_api.py` |
| Sync, fetch, annual average and assign commands | `air_quality/management/commands/` |
| School model and `get_current_reading` | `schools/models.py` |
| School import | `schools/management/commands/import_schools.py` |
| Childcare model and import | `childcare/models.py`, `childcare/management/commands/import_childcare.py` |
| Data sent to the map | `maps/views.py` |
| The map and popups | `maps/templates/maps/map.html` |
| The schedule | `mycron.txt` |
| Data preparation (GIAS, Ofsted, LAEI) | `build_slice.py` in the `school-pollution-analyses` repo |

`schools/management/commands/` also holds some older commands from the first version (`fetch_laqn_data`, `fetch_breathe_london_data`, `import_laqn_sensors`, `calculate_sensor_stats`, `import_laei`). The `air_quality` commands above are the current ones; the older ones are worth checking and removing if nothing uses them.
