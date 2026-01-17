![](/docs/images/Ax_Page_Banner_2500x168_01.png)

# Firmware Update Decision Tree

## Contents
- [Firmware Update Decision Tree](#firmware-update-decision-tree)
  - [Contents](#contents)
  - [Prerequisites for All Firmware Updates](#prerequisites-for-all-firmware-updates)
  - [Overview](#overview)
  - [Decision Flowchart](#decision-flowchart)
  - [Quick Reference Table](#quick-reference-table)
  - [Three-Step Process](#three-step-process)
    - [Step 1: Enable Updates (One-Time Per Board)](#step-1-enable-updates-one-time-per-board)
    - [Step 2: Update Firmware (Simple Cases)](#step-2-update-firmware-simple-cases)
    - [Step 3: Update Firmware (Complex Cases)](#step-3-update-firmware-complex-cases)
  - [Common Scenarios](#common-scenarios)
    - [Scenario A: Brand New Board, Single Device](#scenario-a-brand-new-board-single-device)
    - [Scenario B: Existing Board, Routine Update, Single Device](#scenario-b-existing-board-routine-update-single-device)
    - [Scenario C: Multiple Devices](#scenario-c-multiple-devices)
    - [Scenario D: Windows User](#scenario-d-windows-user)
    - [Scenario E: Board Not Working / Recovery](#scenario-e-board-not-working--recovery)
  - [Key Safety Rules](#key-safety-rules)
  - [Still Unsure?](#still-unsure)
  - [Document Links](#document-links)

## Prerequisites for All Firmware Updates

Before starting any firmware procedure:
-  Voyager SDK installed
-  Virtual environment activated (`source venv/bin/activate`)
-  Administrative privileges on your system
-  Stable power supply (no risk of power loss during update)
-  Linux system (or Linux host for Windows users)

---

## Overview
This guide helps you determine which firmware update procedure to follow based on your board's current state.


## Decision Flowchart

```
START: Do you need to update firmware?
│
├─> Is this a NEW board or are you UNSURE if updates are enabled?
│   │
│   └─> YES → Go to: Enable Card Firmware Update Guide
│       │     (docs/tutorials/enable_updates.md)
│       │
│       └─> THEN → Continue below to update firmware
│
├─> Have you already enabled updates on this board?
│   │
│   ├─> YES, and this is a SIMPLE UPDATE (single device, already updated before)
│   │   │
│   │   └─> Go to: Quick Firmware Update Guide
│   │       (docs/tutorials/quick_firmware_update.md)
│   │
│   └─> YES, but COMPLEX SCENARIO (first time updating, multiple devices, or recovery)
│       │
│       └─> Go to: Full Firmware Update Guide
│           (docs/tutorials/firmware_flash_update.md)
│
└─> Is your system NOT WORKING or needs RECOVERY?
    │
    └─> Go to: Full Firmware Update Guide
        (docs/tutorials/firmware_flash_update.md)
```

---

## Quick Reference Table

| Your Situation | Which Guide | Why |
|---------------|-------------|-----|
| **Brand new board** | [Enable Updates](enable_updates.md) first → then update | New boards need enablement before any firmware update |
| **Unknown if enabled** | [Enable Updates](enable_updates.md) first → then update | Safe to re-run enablement; prevents bricking |
| **Already enabled, routine update, single device** | [Quick Update](quick_firmware_update.md) | Fastest path for simple updates |
| **Already enabled, multiple devices** | [Full Update](firmware_flash_update.md) | Handles complex multi-device scenarios |
| **First time updating this board** | [Full Update](firmware_flash_update.md) | Comprehensive instructions with safety checks |
| **Recovery needed** | [Full Update](firmware_flash_update.md) | Includes troubleshooting and recovery steps |
| **Windows user** | [Full Update](firmware_flash_update.md) | Contains Linux requirement note and workarounds |

---

## Three-Step Process

### Step 1: Enable Updates (One-Time Per Board)

**Document:** [Enable Card Firmware Update Guide](enable_updates.md)

**When to use:**
- New board out of the box
- Unsure if updates are enabled
- Better safe than sorry (re-running is harmless)

**What it does:**
- Downloads and runs `enable_bootloader_update.sh`
- Enables the bootloader update functionality
- Must be done once per board before any firmware updates

---

### Step 2: Update Firmware (Simple Cases)

**Document:** [Quick Firmware Update Guide](quick_firmware_update.md)

**When to use:**
- Board already enabled for updates (Step 1 completed)
- Single device system
- You've updated this board before
- Just need the latest firmware

**What it does:**
- Runs `interactive_flash_update.sh`
- Guides you through power cycling
- Updates to latest firmware version

---

### Step 3: Update Firmware (Complex Cases)

**Document:** [Firmware Update Guide](firmware_flash_update.md)

**When to use:**
- Multiple Metis cards or PCIe card with 4 cores
- First time updating this particular board
- Need troubleshooting or recovery procedures
- Linux requirement matters (Windows users)

**What it does:**
- Comprehensive update procedure
- Per-device targeting with `--device` flag
- Automatic multi-device detection
- Safety checks and recovery procedures
- Troubleshooting section

---

## Common Scenarios

### Scenario A: Brand New Board, Single Device
1. Follow [Enable Updates Guide](enable_updates.md)
2. Power cycle
3. Follow [Quick Update Guide](quick_firmware_update.md)

### Scenario B: Existing Board, Routine Update, Single Device
1. Follow [Quick Update Guide](quick_firmware_update.md) directly

### Scenario C: Multiple Devices
1. If unsure about enablement: [Enable Updates Guide](enable_updates.md) for each device
2. Follow [Full Update Guide](firmware_flash_update.md) - use automatic multi-device update or per-device targeting

### Scenario D: Windows User
1. Must use Linux system temporarily for firmware update
2. Follow [Enable Updates Guide](enable_updates.md) on Linux if needed
3. Follow [Full Update Guide](firmware_flash_update.md) on Linux
4. Reconnect board to Windows after update complete

### Scenario E: Board Not Working / Recovery
1. Follow [Full Update Guide](firmware_flash_update.md)
2. Check Troubleshooting section
3. Contact support if recovery fails

---

## Key Safety Rules

 **CRITICAL:** Never update firmware without first enabling updates - this can brick your board

 **Safe:** Re-running the enable updates procedure is harmless and recommended if unsure

 **Never modify:** Do not edit `interactive_flash_update.sh` - contact Axelera support instead

 **Always back up:** Save important work before firmware updates

 **Power cycling:** Follow power cycle instructions exactly - complete power off required (not restart)

---

## Still Unsure?

**Default recommendation:** If you're uncertain, follow this path:
1. Run [Enable Updates Guide](enable_updates.md) (safe to repeat)
2. Use [Full Update Guide](firmware_flash_update.md) (comprehensive, covers all cases)

**Contact support:** If you encounter any issues or have questions about your specific setup, contact Axelera AI support before proceeding.

---

## Document Links

- [Enable Card Firmware Update Guide](/docs/tutorials/enable_updates.md)
- [Quick Firmware Update Guide](/docs/tutorials/quick_firmware_update.md)
- [Firmware Update Guide (Full)](/docs/tutorials/firmware_flash_update.md)
- [Installation Guide](/docs/tutorials/install.md)
- [Quick Start Guide](/docs/tutorials/quick_start_guide.md)
