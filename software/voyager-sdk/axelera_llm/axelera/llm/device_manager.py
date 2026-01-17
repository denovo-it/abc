# Copyright Axelera AI, 2025
# Utility functions used by the Voyager SDK
from __future__ import annotations

import abc
import os
import sys
import time
from typing import TYPE_CHECKING, Any

from axelera import runtime

from . import config, logging_utils, utils

if TYPE_CHECKING:
    from . import inf_tracers, logging_utils, utils

    Tracers = list[inf_tracers.Tracer]

LOG = logging_utils.getLogger(__name__)


class DeviceManager(abc.ABC):
    """Handle aipu device configuration and own the device.

    Create a device manager using :func:`create_device_manager` and use it as a context manager
    or ensure you release the device using :meth:`release` when you are done with it.
    """

    @abc.abstractmethod
    def release(self) -> None:
        '''Release any resources held by the device manager'''

    @abc.abstractmethod
    def get_metis_type(self) -> config.Metis:
        '''Get the metis type of the (first) device.'''

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()


class _NullDeviceManager(DeviceManager):
    def configure_boards_and_tracers(self, nn, tracers):
        return tracers

    def release(self) -> None:
        pass

    def get_metis_type(self) -> config.Metis:
        return config.Metis.none

    @property
    def devices(self):
        return []


def _device_index(devices, sel):
    try:
        x = int(sel)
        if x < 0 or x >= len(devices):
            raise ValueError(f"Device selector {sel} out of range")
        return x
    except ValueError:
        matching = [idx for idx, d in enumerate(devices) if d.name == sel]
        if not matching:
            raise ValueError(f"No device found matching {sel}")
        return matching[0]


def _select_devices(available, selector):
    if selector:
        indexes = [_device_index(available, s) for s in selector.split(',')]
        devices = [available[i] for i in indexes]
        if not devices:
            raise RuntimeError(f"No devices found matching {selector}")
    else:
        devices = available
    verb = 'Selected' if selector else 'Using'
    names = ', '.join(d.name for d in devices)
    devices_s = 's' if len(devices) > 1 else ''
    deselected = len(available) - len(devices)
    deselected_s = '' if deselected == 1 else 's'
    deselected = f" (deselected {deselected} other device{deselected_s})" if deselected else ''
    log = LOG.info if deselected else LOG.debug
    log(f"{verb} device{devices_s} {names}{deselected}")
    return devices


def _human_readable(key, value):
    if key.startswith('mvm_utilisation_core_') and type(value) in (int, float):
        return f"{value}%"
    if key.startswith('clock_profile_core_') and type(value) is int:
        if value >= 1000:
            return f"{value/1000}GHz"
        return f"{value}MHz"
    return value


class _AipuDeviceManager(DeviceManager):
    def __init__(self, override_metis=config.Metis.none, device_selector: str = ''):
        self.context = runtime.Context()
        try:
            devices = self.context.list_devices()
            if not devices:
                raise RuntimeError("No devices found")
        except RuntimeError as e:
            if override_metis == config.Metis.none:
                raise
            LOG.info(f"Failed to detect device: {e}")
            self.devices = []
            self.metis = override_metis
        else:
            self.devices = _select_devices(devices, device_selector)
            m = _board_type_as_metis(self.devices[0].board_type, self.devices[0].name)
            self.metis = m if override_metis == config.Metis.none else override_metis

    def _configure_boards(self, nn) -> dict[int, int]:
        core_index = 0
        configures = {}
        for task in nn.tasks:
            if not task.is_dl_task:
                continue
            cores = task.aipu_cores
            last = core_index + cores
            clock = nn.model_infos.clock_profile(task.model_info.name, self.metis)
            mvm = nn.model_infos.mvm_limitation(task.model_info.name, self.metis)
            configures.update(_get_configures(core_index, last, clock, mvm))
            core_index = last

        if configures:
            conf = ', '.join(f"{k}={_human_readable(k, v)}" for k, v in configures.items())
            LOG.debug("Reconfiguring devices with %s", conf)
            ready = [self.context.configure_device(d, **configures) for d in self.devices]
            if not all(ready):
                with utils.spinner():
                    while not all(self.context.device_ready(d) for d in self.devices):
                        time.sleep(0.3)
        return _get_core_clocks(self.context, self.devices[0], 0, last)

    def configure_boards_and_tracers(self, nn, tracers):
        core_clocks = self._configure_boards(nn)
        new_tracers = []
        devices = [d.name for d in self.devices]
        for tracer in tracers:
            try:
                tracer.initialize_models(nn.model_infos, self.metis, core_clocks, devices)
            except Exception as e:
                LOG.warning(f"{e}, skip trace")
            else:
                new_tracers.append(tracer)
        return new_tracers

    def get_metis_type(self) -> config.Metis:
        return self.metis

    def release(self) -> None:
        self.context.release()


def create_device_manager(
    pipe_type: str,
    override_metis: config.Metis = config.Metis.none,
    deploy_mode: config.DeployMode = config.DeployMode.QUANTCOMPILE,
    device_selector: str = '',
) -> DeviceManager:
    '''Create a device manager for the given pipe type.

    Use it as a context manager or ensure you release the device using :meth:`release` when you are
    done with it.

    `override_metis` can be used to force the metis type to a specific value.  This is used to
    override the detected type and only impacts limitations normally applied to core on M.2 to
    control power restrictions.

    `device_selector` can be used to select a specific device by name or index.  If empty, all
    available devices will be used.  Alternatively it can be a commma seperated list of device
    indexes or device names as returned by axdevice.
    '''
    if pipe_type not in ['torch', 'quantized'] and deploy_mode not in (
        config.DeployMode.QUANTIZE,
        config.DeployMode.QUANTIZE_DEBUG,
    ):
        try:
            return _AipuDeviceManager(override_metis, device_selector)
        except OSError as e:
            info_or_error = LOG.info if sys.platform == 'darwin' else LOG.error
            info_or_error(f"Failed to create device manager: {e}")

    return _NullDeviceManager()


def detect_metis_type() -> config.Metis:
    '''Quickly detect metis type without creating a device manager.

    On failure returns config.Metis.none so this can be used as a light touch
    detection.
    '''
    try:
        dm = create_device_manager('gst')
    except (OSError, RuntimeError) as e:
        LOG.debug(f"Failed to create device manager: {e}")
        return config.Metis.none
    with dm:
        return dm.get_metis_type()


def _board_type_as_metis(board_type: runtime.BoardType, name: str) -> config.Metis:
    if board_type.name == 'm2':
        return config.Metis.m2
    if board_type.name.startswith('alpha'):
        raise RuntimeError(f"Failed to detect {name}")
    if board_type.name not in ('pcie', 'sbc'):
        LOG.warning(f"Unknown board type {board_type.name} from device {name}, assuming pcie")
    return config.Metis.pcie


def _get_core_clocks(
    ctx: runtime.Context, d: runtime.DeviceInfo, first: int, last: int
) -> dict[int, int]:
    '''Get the current clock frequencies of the cores AIPU device in MHz'''
    cfg = ctx.read_device_configuration(d)
    clocks = {n: cfg.get(f'clock_profile_core_{n}', None) for n in range(first, last)}
    default = {n: config.DEFAULT_CORE_CLOCK for n in range(first, last)}
    if any(v is None for v in clocks.values()):
        LOG.warning("No clock profile found in device configuration")
        return default
    try:
        return {n: int(v) for n, v in clocks.items()}
    except ValueError as e:
        LOG.warning(
            "Unparseable frequency from read_device_configuration: %s, assuming %s",
            e,
            default,
        )
        return default


def _get_configures(
    first_core: int, last_core: int, core_clock: int, mvm_limitation: int
) -> dict[str, Any]:
    '''Configure the AIPU board based on the given configuration and env overrides.'''
    val = config.env.configure_board
    if val == '0':
        LOG.debug("Skipping board configuration")
        return {}

    if val != '1':
        parts = val.split(',', 2)
        try:
            if clock := parts[0]:
                core_clock = int(clock)
            if mvm := len(parts) > 1 and parts[1]:
                mvm_limitation = int(mvm)
        except ValueError as e:
            msg = str(e).capitalize()  # for consistency, 'invalid literal...'
            raise ValueError(f"Badly formatted AXELERA_CONFIGURE_BOARD : {msg}") from None

    configures = {}
    if first_core == 0:
        configures['device_firmware'] = '1'
    for core in range(first_core, last_core):
        configures[f'mvm_utilisation_core_{core}'] = mvm_limitation
        configures[f'clock_profile_core_{core}'] = core_clock
    return configures
