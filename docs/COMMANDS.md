# Command cheat sheet

*Copy-and-paste commands for everyday checks and jobs. Written 13 November 2026. For how the parts fit together, see `docs/HOW_IT_WORKS.md`.*

Run everything from the project folder, with the venv active:

```
cd ~/Projects/schools_air_quality_msp4
source venv/bin/activate
```

The prompt starts with `(venv)` when the venv is active. VS Code's terminal does this for you.

---

## Start of a working session

1. **Did the scheduled jobs run?**
   ```
   grep "===" /tmp/sensor_fetch.log | tail -6
   ```
   Shows the last six run headings. `=== <date>` is a fetch, `=== assign <date>` is an assign. The newest should be from the last hour the Mac was awake.

2. **If the Mac has been asleep, catch up now** rather than waiting for the next hour:
   ```
   python manage.py fetch_all_readings --hours=48
   python manage.py assign_sensors
   ```

3. **Start the site:**
   ```
   python manage.py runserver
   ```
   Open http://127.0.0.1:8000, and press **Cmd + Shift + R** to reload without the cache. Stop the server with **Ctrl + C**.

---

## The schedule (cron)

| Task | Command |
|---|---|
| See what cron is running | `crontab -l` |
| Install `mycron.txt` (replaces the current schedule) | `crontab mycron.txt` |
| Stop all scheduled jobs (`mycron.txt` stays as it is) | `crontab -r` |
| See the last run headings | `grep "===" /tmp/sensor_fetch.log \| tail -6` |
| See the end of the log | `tail -40 /tmp/sensor_fetch.log` |
| When was the log last written to? | `ls -l /tmp/sensor_fetch.log` |
| Any permission errors? | `grep -c PermissionError /tmp/sensor_fetch.log` |

Editing `mycron.txt` changes nothing until you run `crontab mycron.txt`. The log is emptied when the Mac restarts.

---

## Sensors

### Which sensors are online, and when did each last report?

```
python manage.py shell -c "
from django.utils import timezone
from air_quality.models import Sensor
now = timezone.now()
for s in Sensor.objects.filter(is_active=True).order_by('network', 'site_code'):
    r = s.get_latest_reading()
    if r:
        hours = (now - r.timestamp).total_seconds() / 3600
        print(f'{s.network:8} {s.site_code:9} {s.get_site_type_display():17} {timezone.localtime(r.timestamp):%d %b %H:%M}  ({hours:.0f} h ago)')
    else:
        print(f'{s.network:8} {s.site_code:9} {s.get_site_type_display():17} no readings')
"
```

Anything over 168 hours (7 days) ago, or with no readings, is left out by `assign_sensors`.

### One sensor in detail

```
python manage.py shell -c "
from air_quality.models import Sensor
s = Sensor.objects.get(site_code='BL0084')
r = s.get_latest_reading()
print(s.site_code, s.name, '|', s.get_network_display(), '|', s.get_site_type_display(), '| active:', s.is_active)
print('device:', s.metadata.get('device_code'), '| started:', s.metadata.get('start_date'))
print('latest:', r.timestamp if r else 'none', '| NO2', r.no2 if r else '', '| PM2.5', r.pm25 if r else '')
"
```

Change `BL0084` to any site code.

### Update the sensor lists

Run these when sensors may have changed (new installations, closures). Each one only adds or updates; none of them deletes sensors.

```
python manage.py sync_laqn_sensors
python manage.py sync_breathe_sensors
python manage.py sync_aqe_sensors          # only once the AQE site is back
```

Then fetch readings and do a dry run (below), so new sensors are picked up.

---

## Readings

| Task | Command |
|---|---|
| Fetch all networks, last 48 hours | `python manage.py fetch_all_readings --hours=48` |
| Fill a longer gap (a week) | `python manage.py fetch_all_readings --hours=168` |
| One network only | `python manage.py fetch_laqn_readings --hours=48` (or `fetch_breathe_readings`, `fetch_aqe_readings`) |
| One sensor only | `python manage.py fetch_breathe_readings --hours=48 --sensor=BL0084` |

Readings already in the database are left alone, so fetching the same hours twice is safe. "0 readings created" just means nothing new.

---

## Annual averages

### See them

```
python manage.py shell -c "
from air_quality.models import SensorAnnualStats
for a in SensorAnnualStats.objects.select_related('sensor').order_by('sensor__network', 'sensor__site_code', '-year'):
    period = f'{a.period_start} to {a.period_end}' if a.period_start else 'calendar year'
    print(f'{a.sensor.network:8} {a.sensor.site_code:9} {a.year}  {period:26} NO2 {a.no2_mean}  PM2.5 {a.pm25_mean}  capture {a.capture_rate}')
"
```

### Update them

| Task | Command |
|---|---|
| LAQN and AQE, last calendar year | `python manage.py fetch_annual_stats` |
| A given year | `python manage.py fetch_annual_stats --year=2025` |
| Replace ones already saved | add `--overwrite` |
| Breathe London, last 12 full months (check first) | `python manage.py fetch_breathe_annual_stats --dry-run` |
| Breathe London, save | `python manage.py fetch_breathe_annual_stats` |

The Breathe averages cover a rolling 12 months, so it's worth re-running `fetch_breathe_annual_stats` about **once a month**. Each run updates the saved row. Run `fetch_annual_stats` each January for the year just ended.

---

## Which sensor each school uses

### Check what would change, then save

```
python manage.py assign_sensors --dry-run
python manage.py assign_sensors
```

The dry run shows the summary without saving. The hourly cron job runs the second line at 10 past each hour.

### Counts by data source

```
python manage.py shell -c "
from django.db.models import Count
from schools.models import School
for row in School.objects.values('data_source').annotate(n=Count('id')).order_by('data_source'):
    print(row['data_source'], row['n'])
for row in School.objects.filter(data_source='ADJUSTED').values('reference_sensor__network').annotate(n=Count('id')):
    print('  adjusted using', row['reference_sensor__network'], row['n'])
"
```

### One school in detail

```
python manage.py shell -c "
from schools.models import School
s = School.objects.filter(name__icontains='Stockwell').first()
print(s.name, '|', s.data_source)
print('direct:', s.direct_sensor, s.direct_sensor_distance, 'm')
print('spare: ', s.reference_sensor, s.reference_sensor_distance, 'm')
r = s.get_current_reading()
print('method:', r['method'], '| confidence:', r['confidence'], '| NO2', r['no2'], '| PM2.5', r['pm25'], '| PM10', r['pm10'])
"
```

Change `Stockwell` to part of any school's name. It shows the first match.

### The direct schools and their spares

```
python manage.py shell -c "
from schools.models import School
for s in School.objects.filter(data_source='DIRECT'):
    spare = s.reference_sensor
    print(s.name, '|', s.direct_sensor.site_code, '|', spare.site_code if spare else 'no spare', spare.network if spare else '', s.reference_sensor_distance)
"
```

---

## Air Quality England: is it back?

```
curl -sL -o /dev/null -w "%{http_code} %{content_type}\n" https://airqualityengland.co.uk/assets/openair/R_data/SWK08_2025.RData
```

- `200 text/html`: still down (you got the maintenance page).
- Anything that isn't `text/html`: it's back. See "AQE comes back online" in `docs/HOW_IT_WORKS.md` and the roadmap for the steps.

---

## Django

| Task | Command |
|---|---|
| Check the project for problems | `python manage.py check` |
| After changing a model: make a migration | `python manage.py makemigrations` |
| Apply migrations to the database | `python manage.py migrate` |
| Open the Django shell | `python manage.py shell` |
| Run one line of Python with Django loaded | `python manage.py shell -c "..."` |

---

## Git

| Task | Command |
|---|---|
| What has changed? | `git status --short` |
| Show the changes in a file | `git diff path/to/file` |
| Recent commits | `git log --oneline -5` |
| Stage files | `git add path/to/file another/file` |
| Commit | `git commit -m "What changed and why"` |
| Undo changes to a file (not yet staged) | `git restore path/to/file` |
| Send commits to GitHub | `git push` |

`git restore` throws away your changes to that file, so check with `git diff` first.

---

## Good habits

- **Dry run first** whenever a command has `--dry-run`.
- **Commit after each working step**, so there's always a good version to go back to.
- **Never commit `.env`.** It holds your keys and is not in Git. Keep a copy somewhere safe, such as a password manager.
- **A gap in the database isn't always a gap at the site.** Some sites publish late; a bigger `--hours` often fills it.
