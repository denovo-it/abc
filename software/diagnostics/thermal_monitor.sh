#!/bin/bash
# thermal_monitor.sh — Monitora temperature in background durante la pipeline
# Uso: ./thermal_monitor.sh &
# Stop: kill %1  oppure  kill $(cat diagnostics/thermal_monitor.pid)

DIAG_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$DIAG_DIR/thermal_log_$(date +%Y%m%d).csv"
PID_FILE="$DIAG_DIR/thermal_monitor.pid"
INTERVAL=5
WARN_THRESHOLD=80000  # milligradi (80°C)

# Zone termiche (RK3588)
ZONES=(
    "/sys/class/thermal/thermal_zone0/temp:soc"
    "/sys/class/thermal/thermal_zone1/temp:bigcore0"
    "/sys/class/thermal/thermal_zone2/temp:bigcore1"
    "/sys/class/thermal/thermal_zone3/temp:littlecore"
    "/sys/class/thermal/thermal_zone4/temp:center"
    "/sys/class/thermal/thermal_zone5/temp:gpu"
    "/sys/class/thermal/thermal_zone6/temp:npu"
)

cleanup() {
    rm -f "$PID_FILE"
    echo "thermal_monitor: stopped ($(date '+%Y-%m-%d %H:%M:%S'))"
    exit 0
}
trap cleanup SIGTERM SIGINT

# Scrivi header se file nuovo
if [ ! -f "$LOG_FILE" ]; then
    echo "timestamp,soc,bigcore0,bigcore1,littlecore,center,gpu,npu" > "$LOG_FILE"
fi

echo $$ > "$PID_FILE"
echo "thermal_monitor: avviato (PID $$, log: $LOG_FILE, intervallo: ${INTERVAL}s)"

while true; do
    TS=$(date '+%Y-%m-%d %H:%M:%S')
    LINE="$TS"
    WARNINGS=""

    for zone_info in "${ZONES[@]}"; do
        path="${zone_info%%:*}"
        name="${zone_info##*:}"
        temp=$(cat "$path" 2>/dev/null || echo "0")
        temp_c=$((temp / 1000))
        LINE="$LINE,$temp_c"

        if [ "$temp" -ge "$WARN_THRESHOLD" ]; then
            WARNINGS="$WARNINGS $name=${temp_c}°C"
        fi
    done

    echo "$LINE" >> "$LOG_FILE"

    if [ -n "$WARNINGS" ]; then
        echo "WARNING $(date '+%H:%M:%S') TEMPERATURA ALTA:$WARNINGS" | tee -a "$LOG_FILE.warnings"
    fi

    sleep "$INTERVAL"
done
