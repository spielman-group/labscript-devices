# Distinct from utils.py, whose contents do not need PyDAQmx installed, as this does.
import ctypes
import PyDAQmx as daqmx
import PyDAQmx.DAQmxConstants as c
import PyDAQmx.DAQmxTypes as types


def get_devices():
    BUFSIZE = 4096
    result = ctypes.create_string_buffer(BUFSIZE)
    daqmx.DAQmxGetSysDevNames(result, types.uInt32(BUFSIZE))
    return result.value.decode('utf8').split(',')


def get_product_type(device_name):
    BUFSIZE = 4096
    result = ctypes.create_string_buffer(BUFSIZE)
    daqmx.DAQmxGetDevProductType(device_name, result, types.uInt32(BUFSIZE))
    return result.value.decode('utf8')


def get_CI_chans(device_name):
    BUFSIZE = 4096
    result = ctypes.create_string_buffer(BUFSIZE)
    daqmx.DAQmxGetDevCIPhysicalChans(device_name, result, types.uInt32(BUFSIZE))
    return result.value.decode('utf8').split(', ')


def is_simulated(device_name):
    result = types.bool32()
    daqmx.DAQmxGetDevIsSimulated(device_name, result)
    return result.value


def supports_period_measurement(device_name):
    import warnings

    with warnings.catch_warnings():
        # PyDAQmx warns about a positive return value, but actually this is how you are
        # supposed to figure out the size of the array required.
        warnings.simplefilter("ignore")
        # Pass in null pointer and 0 len to ask for what array size is needed:
        npts = daqmx.DAQmxGetDevCISupportedMeasTypes(device_name, types.int32(), 0)
    result = (types.int32 * npts)()
    daqmx.DAQmxGetDevCISupportedMeasTypes(device_name, result, npts)
    return c.DAQmx_Val_Period in [result[i] for i in range(npts)]


def clear_tasks(*tasks):
    """Clear each task that is not None, then raise the first error any raised.

    Every one is cleared whatever the others do: a task left uncleared stays held by
    the driver, and its device fails until the driver is reset.
    """
    error = None
    for task in tasks:
        if task is not None:
            try:
                task.ClearTask()
            except Exception as e:
                error = error or e
    if error is not None:
        raise error


def incomplete_sample_detection(device_name):
    """Return whether the device discards the first edge of a period measurement."""
    # See www.ni.com/documentation/en/ni-daqmx/latest/devconsid/incompletesampledetection/
    # Method credited to Kevin Price: forums.ni.com/t5/Multifunction-DAQ/_/td-p/3849429
    # Hopefully to be deprecated if and when NI lets this feature be inspected, or disabled.

    if is_simulated(device_name):
        msg = (
            "Can only test for incomplete sample detection on a non-simulated device, "
            f"and {device_name} is simulated."
        )
        raise ValueError(msg)

    if not supports_period_measurement(device_name):
        msg = (
            f"{device_name} does not support period measurement, which the test for "
            "incomplete sample detection needs."
        )
        raise ValueError(msg)

    CI_chans = get_CI_chans(device_name)

    if len(CI_chans) < 2:
        msg = (
            "The test for incomplete sample detection needs two counters, and "
            f"{device_name} has {len(CI_chans)}."
        )
        raise ValueError(msg)

    out_chan = CI_chans[0]
    meas_chan = CI_chans[1]

    out_task = daqmx.Task()
    meas_task = None
    try:
        out_task.CreateCOPulseChanTime(
            out_chan, "", c.DAQmx_Val_Seconds, c.DAQmx_Val_Low, 0, 1e-3, 1e-3
        )
        # Prevent the signal being output on the physical terminal:
        out_task.SetCOPulseTerm("", "")
        # Force CO into idle state to prevent spurious edges when the task is started:
        out_task.TaskControl(c.DAQmx_Val_Task_Commit)

        meas_task = daqmx.Task()
        meas_task.CreateCIPeriodChan(
            meas_chan,
            "",
            1e-3,
            1.0,
            c.DAQmx_Val_Seconds,
            c.DAQmx_Val_Rising,
            c.DAQmx_Val_LowFreq1Ctr,
            10.0,
            0,
            "",
        )
        meas_task.CfgImplicitTiming(c.DAQmx_Val_ContSamps, 1)
        # Specify that we are measuring the internal output of the other counter:
        meas_task.SetCIPeriodTerm("", '/' + out_chan + 'InternalOutput')

        meas_task.StartTask()
        out_task.StartTask()
        out_task.WaitUntilTaskDone(10.0)
        samps_avail = types.uInt32()
        meas_task.GetReadAvailSampPerChan(samps_avail)
        if samps_avail.value == 0:
            # The device discarded the first edge
            return True
        elif samps_avail.value == 1:
            # The device did not discard the first edge
            return False
        else:
            msg = (
                f"Got {samps_avail.value} samples from the test for incomplete sample "
                f"detection on {device_name}, not 0 or 1."
            )
            raise ValueError(msg)
    finally:
        clear_tasks(out_task, meas_task)


if __name__ == '__main__':
    # List whether attached devices have incomplete sample detection:
    print('Device    '.rjust(16), 'Incomplete sample detection')
    for name in get_devices():
        if not is_simulated(name):
            model = get_product_type(name)
            print((model + '    ').rjust(16), end=' ')
            try:
                result = incomplete_sample_detection(name)
            except ValueError as e:
                result = str(e)
            print(result)
