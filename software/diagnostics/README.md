# Diagnostica crash e monitoraggio termico

Script per diagnosticare i freeze/crash dell'Orange Pi 5 Plus durante l'uso della pipeline con NPU Metis.

## File

| File | Descrizione |
|------|-------------|
| `collect_crash_info.sh` | Raccoglie log del boot precedente dopo un reboot |
| `thermal_monitor.sh` | Monitora temperature in background (CSV) |
| `diagnostics.service` | Unit systemd per raccolta automatica al boot |

## Uso rapido

### Dopo un crash/reboot

```bash
cd /home/orangepi/abc/software/diagnostics
./collect_crash_info.sh
```

Crea una cartella `crashes/crash_YYYYMMDD_HHMMSS/` con:
- `journal_prev_boot.log` — log completo del boot precedente
- `kernel_prev_boot.log` — solo messaggi kernel del boot precedente
- `dmesg_current.log` — dmesg del boot corrente

### Monitoraggio temperature durante la pipeline

```bash
cd /home/orangepi/abc/software/diagnostics
./thermal_monitor.sh &
```

Genera `thermal_log_YYYYMMDD.csv` con le temperature ogni 5 secondi di tutte e 7 le zone termiche (soc, bigcore0, bigcore1, littlecore, center, gpu, npu).

Warning automatico se una zona supera 80°C.

Per fermare: `kill $(cat thermal_monitor.pid)`

### Installazione servizio systemd (opzionale)

Per raccogliere automaticamente i log ad ogni boot:

```bash
sudo cp diagnostics.service /etc/systemd/system/abc-diagnostics.service
sudo systemctl daemon-reload
sudo systemctl enable abc-diagnostics.service
```

## Output

I dati raccolti (`crashes/`, `thermal_log_*.csv`) sono esclusi dal repository Git tramite `.gitignore`.
