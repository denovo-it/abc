![](/docs/images/Ax_Page_Banner_2500x168_01.png)
# 1. Temperature Monitoring and Thermal Management Guide

- [1. Temperature Monitoring and Thermal Management Guide](#1-temperature-monitoring-and-thermal-management-guide)
  - [1. Temperature Monitoring Tools](#1-temperature-monitoring-tools)
    - [1.1. During Inference Execution](#11-during-inference-execution)
    - [1.2. Using triton\_trace from Command Line Interface](#12-using-triton_trace-from-command-line-interface)
    - [1.3. In Your Application Code](#13-in-your-application-code)
    - [1.4. Using axmonitor](#14-using-axmonitor)
  - [2. Temperature Settings](#2-temperature-settings)
    - [2.1. Considerations and Throttling](#21-considerations-and-throttling)
    - [2.2. Default Temperature Settings](#22-default-temperature-settings)
  - [3. Configuring Temperature Throttling](#3-configuring-temperature-throttling)
    - [3.1. Setting Software Throttling](#31-setting-software-throttling)
  - [4. Safety Mechanisms](#4-safety-mechanisms)
    - [4.1. Warning Temperature](#41-warning-temperature)
    - [4.2. Shutdown Temperature](#42-shutdown-temperature)
    - [4.3. Frequency Downscaling](#43-frequency-downscaling)
  - [5. Temperature Specifications](#5-temperature-specifications)
    - [5.1. Operating Range](#51-operating-range)

This guide explains how to monitor and manage temperatures on Metis-based products.

## 1. Temperature Monitoring Tools

You can monitor the chip temperature using any of these methods:

### 1.1. During Inference Execution

When running inference using `inference.py`, the temperature is automatically displayed in the output:

```bash
$ ./inference.py yolov8s-coco-onnx media/traffic2_480p.mp4 --no-display
INFO    : Core Temp : 39.0°C
```

This shows the maximum temperature among the 5 internal temperature sensors in Metis.

### 1.2. Using triton_trace from Command Line Interface

To get detailed temperature logs with timestamps from all 5 Metis internal temperature sensors (1x temperature sensor outside of AIPU cores silicon area and 4x temperature sensors for each AIPU core):

```bash
$ triton_trace --slog-level inf:collector
$ triton_trace --slog
[04:58:54.012,603] <inf> collector: core_temps=[35,34,34,35,34]
```

### 1.3. In Your Application Code

To monitor temperature in your application:

```python
from axelera.app import inf_tracers
tracers = inf_tracers.create_tracers('core_temp')
stream = create_inference_stream(
    ...
    tracers=tracers,
)
core_temp = stream.get_all_metrics()['core_temp']
print(f"Core temp is {core_temp.value}".center(90, '='))
```

### 1.4. Using axmonitor

You can monitor device temperatures in real-time using the `axmonitor` tool, which provides a visual interface for monitoring core temperatures and other device metrics. For more details, see the [axmonitor documentation](/docs/tutorials/axmonitor.md).

## 2. Temperature Settings

### 2.1. Considerations and Throttling

Temperature throttling in Metis devices is primarily achieved through two mechanisms:

1. **MVM Maximum Utilization Throttling**: The primary method of thermal management involves limiting the maximum percentage utilization of the Metis In-Memory-Compute block, which performs Matrix-Vector-Multiplications (MVM). When temperature thresholds are exceeded, the system reduces the MVM maximum utilization to maintain safe operating temperatures.

2. **Frequency Scaling**: As a secondary mechanism, the system can reduce the chip frequency when temperatures approach critical thresholds, providing an additional layer of thermal protection.

The throttling mechanism operates as follows:
- When temperature exceeds threshold T (°C), MVM utilization is limited to L%
- When temperature decreases by H hysteresis degrees (°C), the MVM utilization limit is removed

The temperature used for throttling is the maximum temperature across all Metis internal temperature sensors, and throttling is applied uniformly to all AIPU Cores in Metis.

The following table in section 2.2 details the specific temperature thresholds and parameters used for these thermal management mechanisms.

### 2.2. Default Temperature Settings

The following table shows all default temperature settings in Metis:

| Type | Parameter | Default Value | User Configurable | Notes |
|------|-----------|---------------|-------------------|-------|
| Software Throttling | T<sub>s</sub> | 200°C (Effectively Disabled) | Yes | Software-based thermal throttling threshold for temperature-constrained environments |
| | H<sub>s</sub> | 10°C | Yes | |
| | L<sub>s</sub> | 10% | Yes | |
| Hardware Throttling | T<sub>h</sub> | 105°C | No | Backup mechanism if warning signal is unused |
| | H<sub>h</sub> | 10°C | No | |
| | L<sub>h</sub> | 1% | No | |
| Safety Guards | Warning (T<sub>j</sub>) | 95°C | No |  |
| | Shutdown (T<sub>j</sub>) | 120°C | No | Set below absolute maximum (125°C) |
| | Freq Downscaling Start | 110°C | No | Activates after hardware throttling |

> [!NOTE]
> All temperatures in the table above refer to silicon junction temperatures (T<sub>j</sub>), which represent the temperature at the silicon die level. These temperatures are typically higher than the package or ambient temperatures.


## 3. Configuring Temperature Throttling

### 3.1. Setting Software Throttling

You can configure software throttling using the axdevice command line interface:

```bash
$ axdevice --set-sw-throttling=T:H:L
```

Where:
- T: Temperature threshold in Celsius
- H: Hysteresis in Celsius
- L: Throttle rate as percentage

Example: To set temperature threshold to 100°C, hysteresis to 5°C, and throttle rate to 10%:
```bash
$ axdevice --set-sw-throttling=100:5:10
```

To view current settings:
```bash
$ axdevice -v
```

> [!IMPORTANT]
> - Settings apply to all AIPU Cores
> - Settings do not persist across device reboots or firmware reloads
> - After exiting throttling mode, MVM utilization returns to its pre-throttling value

## 4. Safety Mechanisms

### 4.1. Warning Temperature

- Generates a log entry when reached
- Configurable via:
```bash
$ axdevice --set-pvt-warning-threshold 85
```
- Does not persist across reboots

### 4.2. Shutdown Temperature

> [!WARNING]
> - Fixed at default value, as in the table above (non-configurable)
> - Triggers board controller to disable all regulators
> - Requires full power cycle to recover

### 4.3. Frequency Downscaling

- Reduces chip frequency by 100 MHz every second while temperature remains above default threshold (minimum 200 MHz)
- Increases chip frequency by 100 MHz when temperature drops 5°C below the default threshold (e.g., 110°C results in 700 MHz, but reaching 105°C returns frequency to 800 MHz)
- Checks every second if temperature is within 5°C of Shutdown threshold
- Operates independently of MVM-based throttling

## 5. Temperature Specifications

### 5.1. Operating Range

For PCIe and M.2 boards (REV1.1, SDK v1.3.0):
- Operating range: [-20°C, +70°C]
- No loss of function, performance, or lifetime expected in this range

> [!NOTE]
> The temperature operating range specified above refers to ambient temperature, not junction temperature as shown in the table earlier in this document.
