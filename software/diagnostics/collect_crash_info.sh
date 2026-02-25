#!/bin/bash
# collect_crash_info.sh — Raccoglie log del boot precedente dopo un crash/reboot
# Lanciare manualmente o via systemd (diagnostics.service)

DIAG_DIR="$(cd "$(dirname "$0")" && pwd)"
CRASH_DIR="$DIAG_DIR/crashes/crash_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$CRASH_DIR"

echo "=== Raccolta diagnostica crash in $CRASH_DIR ==="

# Log completo boot precedente
echo "[1/3] journalctl -b -1 (boot precedente)..."
if journalctl -b -1 > "$CRASH_DIR/journal_prev_boot.log" 2>&1; then
    echo "  OK: $(wc -l < "$CRASH_DIR/journal_prev_boot.log") righe"
else
    echo "  WARN: boot precedente non disponibile (primo boot dopo installazione?)"
fi

# Solo messaggi kernel del boot precedente
echo "[2/3] journalctl -b -1 -k (kernel boot precedente)..."
if journalctl -b -1 -k > "$CRASH_DIR/kernel_prev_boot.log" 2>&1; then
    echo "  OK: $(wc -l < "$CRASH_DIR/kernel_prev_boot.log") righe"
else
    echo "  WARN: kernel log boot precedente non disponibile"
fi

# dmesg corrente (errori driver al boot)
echo "[3/3] dmesg boot corrente..."
dmesg > "$CRASH_DIR/dmesg_current.log" 2>&1
echo "  OK: $(wc -l < "$CRASH_DIR/dmesg_current.log") righe"

# Filtra errori rilevanti (Metis/Mali/NPU/thermal/panic)
echo ""
echo "=== Errori rilevanti (kernel prev boot) ==="
grep -iE "error|panic|oops|npu|metis|mali|thermal|rknpu|hung|watchdog|oom" \
    "$CRASH_DIR/kernel_prev_boot.log" 2>/dev/null | tail -30 || echo "(nessuno trovato)"

echo ""
echo "=== Errori rilevanti (dmesg corrente) ==="
grep -iE "error|npu|metis|mali|rknpu" \
    "$CRASH_DIR/dmesg_current.log" 2>/dev/null | tail -20 || echo "(nessuno trovato)"

echo ""
echo "Diagnostica salvata in: $CRASH_DIR"
ls -lh "$CRASH_DIR"
