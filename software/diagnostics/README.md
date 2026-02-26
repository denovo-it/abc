# Crash diagnostics and thermal monitoring

Scripts for diagnosing freezes/crashes on the Orange Pi 5 Plus during pipeline operation with Metis NPU.

## Files

| File | Description |
|------|-------------|
| `collect_crash_info.sh` | Collects logs from previous boot after a reboot |
| `thermal_monitor.sh` | Monitors temperatures in background (CSV output) |
| `diagnostics.service` | Systemd unit for automatic collection at boot |

## Quick usage

### After a crash/reboot

```bash
cd /home/orangepi/abc/software/diagnostics
./collect_crash_info.sh
```

Creates a `crashes/crash_YYYYMMDD_HHMMSS/` folder with:
- `journal_prev_boot.log` — full journal from previous boot
- `kernel_prev_boot.log` — kernel messages only from previous boot
- `dmesg_current.log` — dmesg from current boot

### Temperature monitoring during pipeline

```bash
cd /home/orangepi/abc/software/diagnostics
./thermal_monitor.sh &
```

Generates `thermal_log_YYYYMMDD.csv` with temperatures every 5 seconds from all 7 thermal zones (soc, bigcore0, bigcore1, littlecore, center, gpu, npu).

Automatic warning if any zone exceeds 80°C.

To stop: `kill $(cat thermal_monitor.pid)`

### Systemd service installation (optional)

To automatically collect logs at every boot:

```bash
sudo cp diagnostics.service /etc/systemd/system/abc-diagnostics.service
sudo systemctl daemon-reload
sudo systemctl enable abc-diagnostics.service
```

## Output

Collected data (`crashes/`, `thermal_log_*.csv`) is excluded from the Git repository via `.gitignore`.
