#####################################################################
#                                                                   #
# /NI_DAQmx/models/get_capabilities.py                              #
#                                                                   #
# Copyright 2018, Christopher Billington                            #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################
"""Update capabilities.json with the capabilities of every NI-DAQmx device connected
to this computer, to add support for a new model of device.

A simulated device configured through NI-MAX works as well, so the physical device is
not needed. Run it with `python get_capabilities.py`, then run generate_subclasses.py.
"""

import numpy as np
import os
import ctypes
import json
import PyDAQmx
from PyDAQmx import byref, Task
from PyDAQmx.DAQmxTypes import uInt32, bool32, int32, float64
import PyDAQmx.DAQmxConstants as c

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
CAPABILITIES_FILE = os.path.join(THIS_FOLDER, 'capabilities.json')


def string_prop(func):
    """Wrap a PyDAQmx getter that fills a string buffer; the device name is optional."""

    def wrapped(name=None):
        BUFSIZE = 4096
        result = ctypes.create_string_buffer(BUFSIZE)
        if name is None:
            func(result, uInt32(BUFSIZE))
        else:
            func(name, result, uInt32(BUFSIZE))
        return result.value.decode('utf8')

    return wrapped


def bool_prop(func):
    def wrapped(name):
        result = bool32()
        func(name, byref(result))
        return bool(result.value)

    return wrapped


def int32_prop(func):
    def wrapped(name):
        result = int32()
        func(name, byref(result))
        return result.value

    return wrapped


def float64_prop(func):
    def wrapped(name):
        result = float64()
        func(name, byref(result))
        return result.value

    return wrapped


def float64_array_prop(func):
    def wrapped(name):
        import warnings

        with warnings.catch_warnings():
            # PyDAQmx warns about a positive return value, but actually this is how you
            # are supposed to figure out the size of the array required.
            warnings.simplefilter("ignore")
            # Pass in null pointer and 0 len to ask for what array size is needed:
            npts = func(name, byref(float64()), 0)
        result = (float64 * npts)()
        func(name, result, npts)
        result = [result[i] for i in range(npts)]
        return result

    return wrapped


def chans(func):
    """Like string_prop, but return the channels it lists, with the device name stripped."""
    wrapped1 = string_prop(func)

    def wrapped2(name):
        result = wrapped1(name)
        if result:
            return [s.strip('/').split('/', 1)[1] for s in result.split(', ')]
        return []

    return wrapped2


DAQmxGetSysDevNames = string_prop(PyDAQmx.DAQmxGetSysDevNames)
DAQmxGetDevProductType = string_prop(PyDAQmx.DAQmxGetDevProductType)
DAQmxGetDevAnlgTrigSupported = bool_prop(PyDAQmx.DAQmxGetDevAnlgTrigSupported)
DAQmxGetDevDigTrigSupported = bool_prop(PyDAQmx.DAQmxGetDevDigTrigSupported)
DAQmxGetDevAOSampClkSupported = bool_prop(PyDAQmx.DAQmxGetDevAOSampClkSupported)
DAQmxGetDevAOPhysicalChans = chans(PyDAQmx.DAQmxGetDevAOPhysicalChans)
DAQmxGetDevAIPhysicalChans = chans(PyDAQmx.DAQmxGetDevAIPhysicalChans)
DAQmxGetDevDOPorts = chans(PyDAQmx.DAQmxGetDevDOPorts)
DAQmxGetDevDOLines = chans(PyDAQmx.DAQmxGetDevDOLines)
DAQmxGetDevDIPorts = chans(PyDAQmx.DAQmxGetDevDIPorts)
DAQmxGetDevDILines = chans(PyDAQmx.DAQmxGetDevDILines)
DAQmxGetDevTerminals = chans(PyDAQmx.DAQmxGetDevTerminals)
DAQmxGetDevCIPhysicalChans = chans(PyDAQmx.DAQmxGetDevCIPhysicalChans)
DAQmxGetDevDOMaxRate = float64_prop(PyDAQmx.DAQmxGetDevDOMaxRate)
DAQmxGetDevAOMaxRate = float64_prop(PyDAQmx.DAQmxGetDevAOMaxRate)
DAQmxGetDevAIMaxSingleChanRate = float64_prop(PyDAQmx.DAQmxGetDevAIMaxSingleChanRate)
DAQmxGetDevAIMaxMultiChanRate = float64_prop(PyDAQmx.DAQmxGetDevAIMaxMultiChanRate)
DAQmxGetDevAOVoltageRngs = float64_array_prop(PyDAQmx.DAQmxGetDevAOVoltageRngs)
DAQmxGetDevAIVoltageRngs = float64_array_prop(PyDAQmx.DAQmxGetDevAIVoltageRngs)
DAQmxGetPhysicalChanAITermCfgs = int32_prop(PyDAQmx.DAQmxGetPhysicalChanAITermCfgs)
DAQmxGetDevAISimultaneousSamplingSupported = bool_prop(PyDAQmx.DAQmxGetDevAISimultaneousSamplingSupported)


def port_supports_buffered(device_name, port, clock_terminal=None):
    """Empirically determine whether a digital port supports buffered output."""
    all_terminals = DAQmxGetDevTerminals(device_name)
    if clock_terminal is None:
        clock_terminal = all_terminals[0]
    npts = 16
    with Task() as task:
        clock_terminal_full = '/' + device_name + '/' + clock_terminal
        data = np.zeros(npts, dtype=np.uint32)
        task.CreateDOChan(device_name + "/" + port, "", c.DAQmx_Val_ChanForAllLines)
        task.CfgSampClkTiming(
            clock_terminal_full, 100, c.DAQmx_Val_Rising, c.DAQmx_Val_FiniteSamps, npts
        )
        written = int32()
        try:
            task.WriteDigitalU32(
                npts, False, 10.0, c.DAQmx_Val_GroupByScanNumber, data, byref(written), None
            )
        except (
            PyDAQmx.DAQmxFunctions.BufferedOperationsNotSupportedOnSelectedLinesError,
            PyDAQmx.DAQmxFunctions.PhysicalChanNotSupportedGivenSampTimingType653xError,
        ):
            return False
        except (
            PyDAQmx.DAQmxFunctions.CantUsePort3AloneGivenSampTimingTypeOn653xError,
            PyDAQmx.DAQmxFunctions.CantUsePort1AloneGivenSampTimingTypeOn653xError,
        ):
            # Ports that throw this error on 653x devices do support buffered output, though
            # there are requirements that multiple ports be used together.
            return True
        except PyDAQmx.DAQmxFunctions.RouteNotSupportedByHW_RoutingError:
            # Try again with a different terminal
            current_terminal_index = all_terminals.index(clock_terminal)
            if current_terminal_index == len(all_terminals) - 1:
                # There are no more terminals. No terminals can be used as clocks,
                # therefore we cannot do externally clocked buffered output.
                return False
            next_terminal_to_try = all_terminals[current_terminal_index + 1]
            return port_supports_buffered(device_name, port, next_terminal_to_try)
        else:
            return True


def AO_bank_sample_rate(device_name):
    """Return the analog outputs' bank size and the highest sample rate with two of
    them in one bank, or (None, None) if the outputs are not in banks."""
    chans = DAQmxGetDevAOPhysicalChans(device_name)
    Vmin, Vmax = DAQmxGetDevAOVoltageRngs(device_name)[0:2]
    single_rate = DAQmxGetDevAOMaxRate(device_name)
    rates = []
    for chan in chans[1:]:
        with Task() as task:
            for pair_chan in [chans[0], chan]:
                task.CreateAOVoltageChan(
                    device_name + '/' + pair_chan, "", Vmin, Vmax, c.DAQmx_Val_Volts, None
                )
            task.CfgSampClkTiming(
                "", 1000, c.DAQmx_Val_Rising, c.DAQmx_Val_FiniteSamps, 1000
            )
            rate = float64()
            task.GetSampClkMaxRate(rate)
            rates.append(rate.value)
    if not rates or min(rates) >= single_rate:
        return None, None
    # The first output that keeps the single-output rate when paired with ao0 starts
    # the second bank. With none, the rate depends on how many outputs are in use, and
    # there are no banks.
    for n, rate in enumerate(rates, start=1):
        if rate >= single_rate:
            return n, min(rates)
    return None, None


def AI_start_delay(device_name):
    """Empirically determine the analog inputs' start delay in seconds (None without PFI0)."""
    if 'PFI0' not in DAQmxGetDevTerminals(device_name):
        return None
    with Task() as task:
        clock_terminal = '/' + device_name + '/PFI0'
        rate = DAQmxGetDevAIMaxSingleChanRate(device_name)
        Vmin, Vmax = DAQmxGetDevAIVoltageRngs(device_name)[0:2]
        num_samples = 1000
        chan = device_name + '/ai0'
        supp_types = DAQmxGetPhysicalChanAITermCfgs(chan)
        if supp_types & c.DAQmx_Val_Bit_TermCfg_RSE:
            input_type = c.DAQmx_Val_RSE
        elif supp_types & c.DAQmx_Val_Bit_TermCfg_Diff:
            input_type = c.DAQmx_Val_Diff
        elif supp_types & c.DAQmx_Val_Bit_TermCfg_PseudoDIFF:
            input_type = c.DAQmx_Val_PseudoDiff
        task.CreateAIVoltageChan(
            chan, "", input_type, Vmin, Vmax, c.DAQmx_Val_Volts, None
        )
        task.CfgSampClkTiming(
            "", rate, c.DAQmx_Val_Rising, c.DAQmx_Val_ContSamps, num_samples
        )
        task.CfgDigEdgeStartTrig(clock_terminal, c.DAQmx_Val_Rising)

        start_trig_delay = float64()
        delay_from_sample_clock = float64()
        sample_timebase_rate = float64()

        try:
            task.GetStartTrigDelay(start_trig_delay)
        except PyDAQmx.DAQmxFunctions.AttributeNotSupportedInTaskContextError:
            # device does not have a Start Trigger Delay property
            # is likely a dynamic signal acquisition device with filter
            # delays instead.
            start_trig_delay.value = 0
        try:
            task.GetDelayFromSampClkDelay(delay_from_sample_clock)
        except PyDAQmx.DAQmxFunctions.AttributeNotSupportedInTaskContextError:
            # seems simultaneous sampling devices do not have this property,
            # so assume it is zero
            delay_from_sample_clock.value = 0
        task.GetSampClkTimebaseRate(sample_timebase_rate)

    total_delay_in_ticks = start_trig_delay.value + delay_from_sample_clock.value
    total_delay_in_seconds = total_delay_in_ticks / sample_timebase_rate.value
    return total_delay_in_seconds


def AI_filter_delay(device_name):
    """Return a dynamic signal acquisition device's filter delay in sample clock periods."""
    if 'PFI0' not in DAQmxGetDevTerminals(device_name):
        return None
    with Task() as task:
        clock_terminal = '/' + device_name + '/PFI0'
        rate = DAQmxGetDevAIMaxSingleChanRate(device_name)
        Vmin, Vmax = DAQmxGetDevAIVoltageRngs(device_name)[0:2]
        num_samples = 1000
        chan = device_name + '/ai0'
        task.CreateAIVoltageChan(
            chan, "", c.DAQmx_Val_PseudoDiff, Vmin, Vmax, c.DAQmx_Val_Volts, None
        )
        task.CfgSampClkTiming(
            "", rate, c.DAQmx_Val_Rising, c.DAQmx_Val_ContSamps, num_samples
        )
        task.CfgDigEdgeStartTrig(clock_terminal, c.DAQmx_Val_Rising)

        start_filter_delay = float64()
        sample_timebase_rate = float64()

        task.SetAIFilterDelayUnits("", c.DAQmx_Val_SampleClkPeriods)

        task.GetAIFilterDelay("", start_filter_delay)
        task.GetSampClkTimebaseRate(sample_timebase_rate)

    return int(start_filter_delay.value)


def supported_AI_terminal_configurations(device_name):
    """Return each analog input's supported terminations: RSE, NRSE, Diff or PseudoDiff."""
    supp_types = {}
    poss_types = {'RSE': c.DAQmx_Val_Bit_TermCfg_RSE,
                  'NRSE': c.DAQmx_Val_Bit_TermCfg_NRSE,
                  'Diff': c.DAQmx_Val_Bit_TermCfg_Diff,
                  'PseudoDiff': c.DAQmx_Val_Bit_TermCfg_PseudoDIFF}
    chans = DAQmxGetDevAIPhysicalChans(device_name)
    for chan in chans:
        byte = DAQmxGetPhysicalChanAITermCfgs(device_name+'/'+chan)
        chan_types = [key for key, val in poss_types.items() if val & byte]
        supp_types[chan] = chan_types

    return supp_types


def supported_AI_ranges_for_non_differential_input(device_name, AI_ranges):
    """Return the `[Vmin, Vmax]` pairs of AI_ranges that RSE input accepts."""
    chan = device_name + '/ai0'
    supported_ranges = []
    # The largest range may only be available for differential input, so try each:
    for Vmin, Vmax in AI_ranges:
        try:
            with Task() as task:
                task.CreateAIVoltageChan(
                    chan, "", c.DAQmx_Val_RSE, Vmin, Vmax, c.DAQmx_Val_Volts, None
                )
                task.StartTask()
        except PyDAQmx.DAQmxFunctions.InvalidAttributeValueError as e:
            if 'DAQmx_AI_Min' in e.message or 'DAQmx_AI_Max' in e.message:
                # Not supported for non-differential input:
                continue
            raise
        supported_ranges.append([Vmin, Vmax])

    return supported_ranges


def supports_semiperiod_measurement(device_name):
    """Return whether the device lists semiperiod among its counter input measurements."""
    import warnings

    with warnings.catch_warnings():
        # PyDAQmx warns about a positive return value, but actually this is how you are
        # supposed to figure out the size of the array required.
        warnings.simplefilter("ignore")
        # Pass in null pointer and 0 len to ask for what array size is needed:
        npts = PyDAQmx.DAQmxGetDevCISupportedMeasTypes(device_name, int32(), 0)
    result = (int32 * npts)()
    PyDAQmx.DAQmxGetDevCISupportedMeasTypes(device_name, result, npts)
    return c.DAQmx_Val_SemiPeriod in [result[i] for i in range(npts)]


def get_min_semiperiod_measurement(device_name):
    """Return the minimum semiperiod measurement of the chosen counter timebase, in seconds."""
    CI_chans = DAQmxGetDevCIPhysicalChans(device_name)
    CI_chan = device_name + '/' + CI_chans[0]
    # Make a task with a semiperiod measurement
    with Task() as task:
        task.CreateCISemiPeriodChan(CI_chan, '', 1e-100, 1e100, c.DAQmx_Val_Seconds, "")
        try:
            task.StartTask()
        except PyDAQmx.DAQmxFunctions.CtrMinMaxError as e:
            # Parse the error to extract the allowed values:
            CI_ranges = []
            DT_MIN_PREFIX = "Value Must Be Greater Than:"
            DT_MAX_PREFIX = "Value Must Be Less Than:"
            error_lines = e.message.splitlines()
            for line in error_lines:
                if DT_MIN_PREFIX in line:
                    dt_min = float(line.replace(DT_MIN_PREFIX, ''))
                if DT_MAX_PREFIX in line:
                    dt_max = float(line.replace(DT_MAX_PREFIX, ''))
                    CI_ranges.append([dt_min, dt_max])
        else:
            raise AssertionError("Can't figure out counter input ranges")

    # Each timebase measures its own range. Use the fastest one that can still measure
    # 100 s, or else the largest dtmin, as the default min_semiperiod_measurement, the
    # shortest wait monitor pulse. Experiments far from 100 s may pass another.
    for dtmin, dtmax in sorted(CI_ranges):
        if dtmax > 100:
            return dtmin
    return dtmin


if __name__ == '__main__':
    capabilities = {}
    if os.path.exists(CAPABILITIES_FILE):
        with open(CAPABILITIES_FILE) as f:
            try:
                capabilities = json.load(f)
            except ValueError:
                pass

    models = []
    for name in DAQmxGetSysDevNames().split(', '):
        # ignore extra details in model names
        model = DAQmxGetDevProductType(name).split(' ')[0]
        print("found device:", name, model)
        if model not in models:
            models.append(model)
        capabilities[model] = {}
        try:
            capabilities[model]["supports_buffered_AO"] = DAQmxGetDevAOSampClkSupported(
                name
            )
        except PyDAQmx.DAQmxFunctions.AttrNotSupportedError:
            capabilities[model]["supports_buffered_AO"] = False
        try:
            capabilities[model]["max_DO_sample_rate"] = DAQmxGetDevDOMaxRate(name)
            capabilities[model]["supports_buffered_DO"] = True
        except PyDAQmx.DAQmxFunctions.AttrNotSupportedError:
            capabilities[model]["max_DO_sample_rate"] = None
            capabilities[model]["supports_buffered_DO"] = False
        if capabilities[model]["supports_buffered_AO"]:
            capabilities[model]["max_AO_sample_rate"] = DAQmxGetDevAOMaxRate(name)
        else:
            capabilities[model]["max_AO_sample_rate"] = None
        if capabilities[model]["supports_buffered_AO"]:
            bank_size, bank_rate = AO_bank_sample_rate(name)
            if bank_size is not None:
                capabilities[model]["AO_bank_size"] = bank_size
                capabilities[model]["max_AO_bank_sample_rate"] = bank_rate

        capabilities[model]["num_AO"] = len(DAQmxGetDevAOPhysicalChans(name))
        capabilities[model]["num_AI"] = len(DAQmxGetDevAIPhysicalChans(name))
        if capabilities[model]["num_AI"] > 0:
            single_rate = DAQmxGetDevAIMaxSingleChanRate(name)
            multi_rate = DAQmxGetDevAIMaxMultiChanRate(name)
        else:
            single_rate = None
            multi_rate = None
        capabilities[model]["max_AI_single_chan_rate"] = single_rate
        capabilities[model]["max_AI_multi_chan_rate"] = multi_rate
        if capabilities[model]["num_AI"] > 0:
            capabilities[model]["AI_term_cfg"] = supported_AI_terminal_configurations(name)
            cfgs = [item for sublist in capabilities[model]["AI_term_cfg"].values() for item in sublist]
            if cfgs.count('RSE'):
                capabilities[model]["AI_term"] = 'RSE'
            elif cfgs.count('Diff'):
                capabilities[model]["AI_term"] = 'Diff'
            elif cfgs.count('PseudoDiff'):
                capabilities[model]["AI_term"] = 'PseudoDiff'
            capabilities[model]["supports_simultaneous_AI_sampling"] = DAQmxGetDevAISimultaneousSamplingSupported(name)

        capabilities[model]["ports"] = {}
        ports = DAQmxGetDevDOPorts(name)
        chans = DAQmxGetDevDOLines(name)
        for port in ports:
            if '_' in port:
                # Ignore the alternate port names such as 'port0_32' that allow using two or
                # more ports together as a single, larger one:
                continue
            port_info = {}
            capabilities[model]["ports"][port] = port_info
            port_chans = [chan for chan in chans if chan.split('/')[0] == port]
            port_info['num_lines'] = len(port_chans)
            if capabilities[model]["supports_buffered_DO"]:
                port_info['supports_buffered'] = port_supports_buffered(name, port)
            else:
                port_info['supports_buffered'] = False

        capabilities[model]["num_CI"] = len(DAQmxGetDevCIPhysicalChans(name))
        supports_semiperiod = supports_semiperiod_measurement(name)
        capabilities[model]["supports_semiperiod_measurement"] = supports_semiperiod
        if capabilities[model]["num_CI"] > 0 and supports_semiperiod:
            min_semiperiod_measurement = get_min_semiperiod_measurement(name)
        else:
            min_semiperiod_measurement = None
        capabilities[model]["min_semiperiod_measurement"] = min_semiperiod_measurement

        if capabilities[model]['num_AO'] > 0:
            AO_ranges = []
            raw_limits = DAQmxGetDevAOVoltageRngs(name)
            for i in range(0, len(raw_limits), 2):
                Vmin, Vmax = raw_limits[i], raw_limits[i + 1]
                AO_ranges.append([Vmin, Vmax])
            # Find range with the largest maximum voltage and use that:
            Vmin, Vmax = max(AO_ranges, key=lambda range: range[1])
            # Confirm that no other range has a voltage lower than Vmin,
            # since if it does, this violates our assumptions and things might not
            # be as simple as having a single range:
            assert min(AO_ranges)[0] >= Vmin
            capabilities[model]["AO_range"] = [Vmin, Vmax]
        else:
            capabilities[model]["AO_range"] = None

        if capabilities[model]['num_AI'] > 0:
            AI_ranges = []
            raw_limits = DAQmxGetDevAIVoltageRngs(name)
            for i in range(0, len(raw_limits), 2):
                Vmin, Vmax = raw_limits[i], raw_limits[i + 1]
                AI_ranges.append([Vmin, Vmax])
            # Find range with the largest maximum voltage and use that:
            Vmin_raw, Vmax_raw = max(AI_ranges, key=lambda range: range[1])
            # Confirm that no other range has a voltage lower than Vmin,
            # since if it does, this violates our assumptions and things might not
            # be as simple as having a single range:
            assert min(AI_ranges)[0] >= Vmin_raw
            capabilities[model]["AI_range_Diff"] = [Vmin_raw, Vmax_raw]
            if 'RSE' in capabilities[model]["AI_term_cfg"]['ai0']:
                # Now limit to non-differential inputs (if available), which may have lower ranges
                AI_ranges = supported_AI_ranges_for_non_differential_input(name, AI_ranges)
            # Find RSE range with the largest maximum voltage and use that:
            Vmin, Vmax = max(AI_ranges, key=lambda range: range[1])
            assert min(AI_ranges)[0] >= Vmin
            capabilities[model]["AI_range"] = [Vmin, Vmax]
        else:
            capabilities[model]["AI_range"] = None
            capabilities[model]["AI_range_Diff"] = None

        if capabilities[model]["num_AI"] > 0:
            if capabilities[model]["AI_term"] == 'PseudoDiff':
                capabilities[model]["AI_start_delay_ticks"] = AI_filter_delay(name)
                capabilities[model]["AI_start_delay"] = None
            else:
                capabilities[model]["AI_start_delay"] = AI_start_delay(name)
        else:
            capabilities[model]["AI_start_delay"] = None


    with open(CAPABILITIES_FILE, 'w', newline='\n') as f:
        data = json.dumps(capabilities, sort_keys=True, indent=4)
        f.write(data)

    print(f"added/updated capabilities for {len(models)} models")
    print(f"Total models with known capabilities: {len(capabilities)}")
    for model in capabilities:
        if model not in models:
            print(model, 'capabilities not updated')
    print("run generate_subclasses.py to make labscript devices for these models")
