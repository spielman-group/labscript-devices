# /labscript_devices/AlazarTechBoard/blacs_workers.py
#
# Hacked up from NIboard.py by LDT 2017-01-26
#
# Copyright (c) Monash University 2017

import ctypes
import numpy as np
import sys
import time
from tqdm import tqdm

import labscript_devices.atsapi as ats
import labscript_devices.guiless as guiless
from labscript import LabscriptError
import labscript_utils.h5_lock
import h5py
import labscript_utils.properties

tqdm_kwargs = {'file': sys.stdout, 'ascii': False, 'ncols': 80}

# Input range in mV, as the user gives it, to its ATS constant. Only the ranges that
# work with our ATS9462 are here; atsapi has others, which do not.
atsRanges = {
    200: ats.INPUT_RANGE_PM_200_MV,
    400: ats.INPUT_RANGE_PM_400_MV,
    800: ats.INPUT_RANGE_PM_800_MV,
    2000: ats.INPUT_RANGE_PM_2_V,
    4000: ats.INPUT_RANGE_PM_4_V,
}

atsSampleRates = {
    1000:      ats.SAMPLE_RATE_1KSPS,
    2000:      ats.SAMPLE_RATE_2KSPS,
    5000:      ats.SAMPLE_RATE_5KSPS,
    10000:     ats.SAMPLE_RATE_10KSPS,
    20000:     ats.SAMPLE_RATE_20KSPS,
    50000:     ats.SAMPLE_RATE_50KSPS,
    100000:    ats.SAMPLE_RATE_100KSPS,
    200000:    ats.SAMPLE_RATE_200KSPS,
    500000:    ats.SAMPLE_RATE_500KSPS,
    1000000:   ats.SAMPLE_RATE_1MSPS,
    2000000:   ats.SAMPLE_RATE_2MSPS,
    5000000:   ats.SAMPLE_RATE_5MSPS,
    10000000:  ats.SAMPLE_RATE_10MSPS,
    20000000:  ats.SAMPLE_RATE_20MSPS,
    25000000:  ats.SAMPLE_RATE_25MSPS,
    50000000:  ats.SAMPLE_RATE_50MSPS,
    100000000: ats.SAMPLE_RATE_100MSPS,
    125000000: ats.SAMPLE_RATE_125MSPS,
    160000000: ats.SAMPLE_RATE_160MSPS,
    180000000: ats.SAMPLE_RATE_180MSPS
}

atsExternalClockAdvice = {
    'ATS9462': 'a 200mV sine (conservatively peak-to-peak) between 9.5 and 10.5 MHz.'
}


def find_nearest_internal_clock(array, value):
    """Return the element of `array` nearest to `value`."""
    if not isinstance(array, np.ndarray):
        array = np.array(list(array))
    ix = np.abs(array - value).argmin()
    return array[ix]


def find_clock_and_r(f, clocks):
    """Return the clock in `clocks` and the divisor that give a rate at or just above `f`."""
    divisors, remainders = divmod(clocks, f)
    opts_dtypes = [('rem', 'i4'), ('div', 'i4'), ('clock', 'i4')]
    opts = np.array(list(zip(remainders, divisors, clocks)), dtype=opts_dtypes)
    opts.sort(order='rem')
    minrem = opts['rem'][0]
    # This gets the option with minimum remainder and maximum divisor
    bestopt = np.sort(opts[opts['rem'] == minrem], order='div')[-1]
    return bestopt['clock'], bestopt['div']


def ats9462_clock(f):
    """Return (PLL clock, divider) giving a sample rate at or just above `f`."""
    meg = 1000000
    rlimit = 10000
    clocks_allowed = np.arange(150*meg, 181*meg, 1*meg)
    clock, divider = find_clock_and_r(f, clocks_allowed)
    if divider > rlimit:
        raise LabscriptError(
            f"The clock divider {divider:d} for the requested sample rate exceeds "
            f"the maximum of {rlimit:d}. Raise requested_acquisition_rate."
        )
    if clock % divider != 0:
        warning = (
            f"Warning: couldn't match the requested sample rate of {f:f} SPS. "
            f"Using {clock//divider:d} SPS instead."
        )
        print(warning, file=sys.stderr)
    return clock, divider


class AlazarTechBoardWorker(guiless.GuilessWorker):
    """Captures traces on a thread and writes them to the shot file."""

    def init(self):
        global h5py
        import labscript_utils.h5_lock
        import h5py
        from queue import Queue
        import threading

        self.sdk_version = ats.getSDKVersion()
        self.sdk_version_string = '.'.join(map(str, self.sdk_version))
        print(f"AlazarTech SDK version {self.sdk_version_string:s}")

        # Always system 1, board 1: ats_system_id and ats_board_id are not read.
        system_id = 1
        board_id = 1
        self.board = board = ats.Board(systemId=system_id, boardId=board_id)
        self.driver_version_string = '(unknown)'

        self.board_name = ats.boardNames[self.board.type]
        assert self.board_name == "ATS9462", (
            f"Only the ATS9462 is supported at present. This board is an {self.board_name}."
        )
        assert board.num_channels == 2, (
            "Only two-channel boards are supported at present. "
            f"This board has {board.num_channels}."
        )

        print(f"Initialised AlazarTech {self.board_name:s} (SN {board.serial_number:d}) "
              f"connected as system {system_id:d}, board {board_id:d}.")
        print(f"Hardware revision {board.revision_string:s}, driver version "
              f"{self.driver_version_string:s}, CPLD version {board.cpld_version_string:s}.")
        print(f"{board.num_channels:d} channels. Board memory {board.memorysize_samples:d}, "
              f"quantising {board.bits_per_sample:d} bits per sample.")
        # Cancels any asynchronous acquisition left running on the board.
        board.abortAsyncRead()

        self.acquisition_queue = Queue()
        self.acquisition_thread = threading.Thread(
            target=self.acquisition_loop)
        self.acquisition_thread.daemon = True
        self.acquisition_exception = None
        self.acquisition_done = threading.Event()
        self.acquisition_thread.start()
        self.aborting = False

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        # transition_to_manual writes the traces to this file.
        self.h5_file = h5_file
        self.device_name = device_name
        with h5py.File(h5_file, 'r') as hdf5_file:
            print("\nUsing "+h5_file)
            self.device_properties = device_properties = labscript_utils.properties.get(
                hdf5_file, device_name, 'device_properties')

        clock_source_id = device_properties['clock_source_id']
        requested_acquisition_rate = device_properties['requested_acquisition_rate']
        clock_edge_id = device_properties['clock_edge_id']
        if clock_source_id == ats.INTERNAL_CLOCK:
            # The nearest internal rate, which may be below the one requested.
            actual_acquisition_rate = find_nearest_internal_clock(
                atsSampleRates.keys(), requested_acquisition_rate)
            # An ID, not samples per second: setCaptureClock's rate argument takes either.
            atsSamplesPerSec_or_id = atsSampleRates[actual_acquisition_rate]
            decimation = 0  # Must be zero for internal clocking
            clock_edge_id = ats.CLOCK_EDGE_RISING
            print(f'Internal clocking at {actual_acquisition_rate:.0f} samples per second '
                  f'({actual_acquisition_rate/1e6:.1f} MS/s), from internal reference.')
        elif clock_source_id == ats.EXTERNAL_CLOCK_10MHz_REF:
            atsSamplesPerSec_or_id, divisor = ats9462_clock(
                requested_acquisition_rate)
            actual_acquisition_rate = atsSamplesPerSec_or_id // divisor
            decimation = divisor - 1
            clock_edge_id = ats.CLOCK_EDGE_RISING
            print(f'Internal clocking at {actual_acquisition_rate:.0f} samples per second '
                  f'({actual_acquisition_rate/1e6:.1f} MS/s), from the external 10 MHz reference '
                  f'({atsSamplesPerSec_or_id//1000000:d} MHz PLL divided by {divisor:d}).')
        elif clock_source_id == ats.FAST_EXTERNAL_CLOCK:
            raise LabscriptError(
                "Clock source FAST_EXTERNAL_CLOCK is not implemented. "
                "Set clock_source_id to INTERNAL_CLOCK or EXTERNAL_CLOCK_10MHz_REF."
            )
        elif clock_source_id == ats.MEDIUM_EXTERNAL_CLOCK:
            raise LabscriptError(
                "Clock source MEDIUM_EXTERNAL_CLOCK is not implemented. "
                "Set clock_source_id to INTERNAL_CLOCK or EXTERNAL_CLOCK_10MHz_REF."
            )
        elif clock_source_id == ats.SLOW_EXTERNAL_CLOCK:
            raise LabscriptError(
                "Clock source SLOW_EXTERNAL_CLOCK is not implemented. "
                "Set clock_source_id to INTERNAL_CLOCK or EXTERNAL_CLOCK_10MHz_REF."
            )
        elif clock_source_id == ats.EXTERNAL_CLOCK_AC:
            raise LabscriptError(
                "Clock source EXTERNAL_CLOCK_AC is not implemented. "
                "Set clock_source_id to INTERNAL_CLOCK or EXTERNAL_CLOCK_10MHz_REF."
            )
        elif clock_source_id == ats.EXTERNAL_CLOCK_DC:
            raise LabscriptError(
                "Clock source EXTERNAL_CLOCK_DC is not implemented. "
                "Set clock_source_id to INTERNAL_CLOCK or EXTERNAL_CLOCK_10MHz_REF."
            )
        else:
            raise LabscriptError(
                f"Clock source code {clock_source_id} is not recognised. "
                "Set clock_source_id to INTERNAL_CLOCK or EXTERNAL_CLOCK_10MHz_REF."
            )
        # The clock_edge_id parameter is not needed for INTERNAL_CLOCK and
        # EXTERNAL_CLOCK_10MHz_REF modes but is here for future extension
        try:
            self.board.setCaptureClock(
                device_properties['clock_source_id'], atsSamplesPerSec_or_id, clock_edge_id, decimation)
        except ats.AlazarException as e:
            errstring, funcname, arguments, retCode, retText = e.args
            if retText == 'ApiPllNotLocked':
                print("Error: PLL not locked.")
                try:
                    print(f"Error: For this {self.board_name:s} board, the ext reference should be "
                          f"{atsExternalClockAdvice[self.board_name]:s}")
                except KeyError:
                    print(f"Error: There is no advice on clocking the {self.board_name:s} board.")
            raise ats.AlazarException(e)

        # The rate in use can differ from the requested one, so it is saved in the device group.
        with h5py.File(h5_file, 'r+') as hdf5_file:
            hdf5_file['devices'][device_name].attrs.create(
                'acquisition_rate', actual_acquisition_rate, dtype='int32')

        # ETR_5V means +/-5V, and is 8bit
        # So code 150 means (150-128)/128 * 5V = 860mV.
        self.board.setExternalTrigger(
            device_properties['exttrig_coupling_id'], device_properties['exttrig_range_id'])
        print(f"Trigger coupling_id: {device_properties['exttrig_coupling_id']:d}, "
              f"range_id: {device_properties['exttrig_range_id']:d}.")

        self.board.setTriggerOperation(
            device_properties['trig_operation'],
            device_properties['trig_engine_id1'], device_properties['trig_source_id1'],
            device_properties['trig_slope_id1'], device_properties['trig_level_id1'],
            device_properties['trig_engine_id2'], device_properties['trig_source_id2'],
            device_properties['trig_slope_id2'], device_properties['trig_level_id2'])
        print(f"Trigger operation set to operation: {device_properties['trig_operation']:d}")
        print(f"Trigger engine 1 set to {device_properties['trig_engine_id1']:d}, "
              f"source: {device_properties['trig_source_id1']:d}, "
              f"slope: {device_properties['trig_slope_id1']:d}, "
              f"level: {device_properties['trig_level_id1']:d}.")
        print(f"Trigger engine 2 set to {device_properties['trig_engine_id2']:d}, "
              f"source: {device_properties['trig_source_id2']:d}, "
              f"slope: {device_properties['trig_slope_id2']:d}, "
              f"level: {device_properties['trig_level_id2']:d}.")

        # The trigger delay is always 0: trig_delay_samples is not read.
        self.board.setTriggerDelay(0)

        # The board triggers itself if no trigger event comes within the timeout; 0 makes
        # it wait forever. trig_timeout_10usecs is not read: we time out on the readout.
        self.board.setTriggerTimeOut(0)

        # Configure the AUX I/O connector as AUX_OUT_TRIGGER; by default it emits the
        # sample clock. The second parameter is a dummy value for AUX_OUT_TRIGGER.
        self.board.configureAuxIO(ats.AUX_OUT_TRIGGER, 0)

        try:
            chA_range_id = atsRanges[device_properties['chA_input_range']]
        except KeyError:
            raise LabscriptError(
                f"Input range {device_properties['chA_input_range']} mV for channel A is not "
                f"supported. Give chA_input_range in millivolts, as one of {list(atsRanges)}."
            )
        self.board.inputControl(
            ats.CHANNEL_A, device_properties['chA_coupling_id'], chA_range_id, device_properties['chA_impedance_id'])
        self.board.setBWLimit(ats.CHANNEL_A, device_properties['chA_bw_limit'])
        print(f"Channel A input full scale: {device_properties['chA_input_range']:d}, "
              f"coupling: {device_properties['chA_coupling_id']:d}, "
              f"impedance: {device_properties['chA_impedance_id']:d}, "
              f"bandwidth limit: {device_properties['chA_bw_limit']:d}.")

        try:
            chB_range_id = atsRanges[device_properties['chB_input_range']]
        except KeyError:
            raise LabscriptError(
                f"Input range {device_properties['chB_input_range']} mV for channel B is not "
                f"supported. Give chB_input_range in millivolts, as one of {list(atsRanges)}."
            )
        self.board.inputControl(
            ats.CHANNEL_B, device_properties['chB_coupling_id'], chB_range_id, device_properties['chB_impedance_id'])
        self.board.setBWLimit(ats.CHANNEL_B, device_properties['chB_bw_limit'])
        print(f"Channel B input full scale: {device_properties['chB_input_range']:d}, "
              f"coupling: {device_properties['chB_coupling_id']:d}, "
              f"impedance: {device_properties['chB_impedance_id']:d}, "
              f"bandwidth limit: {device_properties['chB_bw_limit']:d}.")

        self.samplesPerBuffer = 204800
        self.oneM = 2**20
        # Timeout in ms of each wait for a buffer; it is not derived from the shot's duration.
        self.timeout = 60000

        self.channels = device_properties['channels']
        if not (self.channels & ats.CHANNEL_A or self.channels & ats.CHANNEL_B):
            raise LabscriptError(
                "The channels keyword must include ats.CHANNEL_A or ats.CHANNEL_B. "
                "Use ats.CHANNEL_A | ats.CHANNEL_B to acquire both."
            )
        self.channelCount = 0
        for c in ats.channels:
            self.channelCount += (c & self.channels == c)

        memorySize_samples, self.bitsPerSample = self.board.getChannelInfo()
        # Bytes per value: bits per sample rounded up to whole bytes.
        self.bytesPerDatum = (self.bitsPerSample + 7) // 8

        print(f"bytesPerDatum = {self.bytesPerDatum:d}. channelcount = {self.channelCount:d}.")
        # One 'sample' is one datum from each channel
        self.bytesPerBuffer = self.bytesPerDatum * \
            self.channelCount * self.samplesPerBuffer

        self.samplesPerAcquisition = int(
            actual_acquisition_rate * device_properties['acquisition_duration'] + 0.5)
        memoryPerAcquisition = self.bytesPerDatum * \
            self.samplesPerAcquisition * self.channelCount
        self.buffersPerAcquisition = ((self.samplesPerAcquisition + self.samplesPerBuffer - 1) //
                                      self.samplesPerBuffer)
        print(f"Acquiring for {device_properties['acquisition_duration']:5.3f}s generates "
              f"{self.samplesPerAcquisition/1e6:5.3f} MS ({memoryPerAcquisition/self.oneM:5.3f} MB total)")
        print(f"Buffers are {self.samplesPerBuffer/1e6:5.3f} MS and {self.bytesPerBuffer:d} bytes. "
              f"Allocating {self.buffersPerAcquisition:d} buffers... ", end='')
        self.board.setRecordSize(0, self.samplesPerBuffer)

        # We know that disk can't keep up, so we preallocate all buffers
        sample_type = ctypes.c_uint16  # It's 16bit
        self.buffers = []
        for i in range(self.buffersPerAcquisition):
            self.buffers.append(ats.DMABuffer(
                sample_type, self.bytesPerBuffer))
        print('done.')

        # This works, but ADMA_ALLOC_BUFFERS is questionable, because atsapi's DMABuffer
        # has already allocated the buffers.
        acqflags = ats.ADMA_TRIGGERED_STREAMING | ats.ADMA_ALLOC_BUFFERS | ats.ADMA_FIFO_ONLY_STREAMING

        # This does not actually start the capture, it just sets it up
        self.board.beforeAsyncRead(self.channels,
                                   0,                 # Trig offset, must be 0
                                   self.samplesPerBuffer,
                                   1,                 # Must be 1
                                   0x7FFFFFFF,        # Ignored
                                   acqflags)

        self.acquisition_queue.put('start')
        # No final front-panel values; None would tell BLACS the transition failed.
        return {}

    # A daemon thread started by init. It waits for 'start', queued by transition_to_buffered,
    # fills the buffers allocated there and sets acquisition_done. transition_to_manual
    # saves and frees the buffers.
    def acquisition_loop(self):
        while True:
            command = self.acquisition_queue.get()
            assert command == 'start'
            self.acquisition_exception = None
            # Only an earlier acquisition can have left this set.
            self.acquisition_done.clear()
            try:
                print(f"Capturing {self.buffersPerAcquisition:d} buffers. ", end="")
                buffersCompleted = 0
                bytesTransferred = 0
                print('Read buffer:', end="")
                with tqdm(total=self.buffersPerAcquisition, unit='buffers', desc='Capturing buffers', **tqdm_kwargs) as pbar:
                    while (buffersCompleted < self.buffersPerAcquisition and not self.aborting):
                        buffer = self.buffers[buffersCompleted]
                        self.board.waitNextAsyncBufferComplete(
                            buffer.addr, self.bytesPerBuffer, timeout_ms=self.timeout)
                        buffersCompleted += 1
                        pbar.update(1)
                        bytesTransferred += buffer.size_bytes
            except ats.AlazarException as e:
                # Assume it came from waitNextAsyncBufferComplete, so e.args are the
                # five items that returnCodeCheck gives.
                errstring, funcname, arguments, retCode, retText = e.args
                print(f"\n\nAPI error string is: {errstring:s}")
                # Kept in shared state for wait_acquisition_complete to raise in the
                # main thread, unless this is an abort.
                self.acquisition_exception = e
                print(f"acquisition thread: acquisition_exception is {self.acquisition_exception}")
                # The finally clause runs, then the loop waits for the next 'start'.
                continue
            except Exception as e:
                print(f"Got some other exception {e}")
                self.acquisition_exception = e
                continue
            finally:
                self.board.abortAsyncRead()
                self.acquisition_done.set()
            if self.aborting:
                print("acquisition thread: capture aborted.")
                continue

    def to_volts(self, zeroToFullScale, buf):
        """Convert unsigned samples to volts; `zeroToFullScale` is the input range in mV."""
        offset = float(2**(self.bitsPerSample-1))
        return (np.asarray(buf, np.float32)-offset)/offset * zeroToFullScale * 0.001

    def wait_acquisition_complete(self):
        """Wait for the acquisition thread; raise its failure or a timeout, unless aborting."""
        try:
            # The flag should be set already. If not, for example because no trigger
            # came, the thread is still waiting for a buffer, for up to self.timeout.
            if not self.acquisition_done.wait(timeout=2) and not self.aborting:
                raise Exception(
                    'Waiting for acquisition to complete timed out')
            if self.acquisition_exception is not None and not self.aborting:
                raise self.acquisition_exception
        finally:
            # Aborting the read makes the acquisition thread's blocked
            # waitNextAsyncBufferComplete return, with an ApiDmaCalled error code
            # in its AlazarException.
            self.board.abortAsyncRead()
            self.acquisition_done.clear()
            self.acquisition_exception = None

    def transition_to_manual(self):
        self.wait_acquisition_complete()
        with h5py.File(self.h5_file, 'r+') as hdf5_file:
            grp = hdf5_file.create_group('/data/traces/'+self.device_name)
            if self.channels & ats.CHANNEL_A:
                dsetA = grp.create_dataset(
                    'channelA',    (self.samplesPerAcquisition,), dtype='float32')
                dsetAraw = grp.create_dataset(
                    'rawsamplesA', (self.samplesPerAcquisition,), dtype='uint16')
            if self.channels & ats.CHANNEL_B:
                dsetB = grp.create_dataset(
                    'channelB',    (self.samplesPerAcquisition,), dtype='float32')
                dsetBraw = grp.create_dataset(
                    'rawsamplesB', (self.samplesPerAcquisition,), dtype='uint16')
            start = 0
            samplesToProcess = self.samplesPerAcquisition
            # A is read from value 0 of each sample and B from value 1, so a lone
            # channel is taken to be A.
            for buf, counter in tqdm(zip(self.buffers, range(1, len(self.buffers)+1)),
                                     unit='buffers', desc='Writing buffers to HDF5', **tqdm_kwargs):
                bufferData = buf.buffer
                # lastI cuts the last buffer, only partly filled, to the samples still needed.
                lastI = (samplesToProcess if (samplesToProcess < self.samplesPerBuffer)
                         else self.samplesPerBuffer) * self.channelCount
                end = start+len(bufferData[0: lastI])//self.channelCount
                if self.channels & ats.CHANNEL_A:
                    dsetAraw[start: end] = bufferData[0: lastI: self.channelCount]
                    dsetA[start: end] = self.to_volts(
                        self.device_properties['chA_input_range'], bufferData[0: lastI: self.channelCount])
                if self.channels & ats.CHANNEL_B:
                    dsetBraw[start: end] = bufferData[1: lastI: self.channelCount]
                    dsetB[start: end] = self.to_volts(
                        self.device_properties['chB_input_range'], bufferData[1: lastI: self.channelCount])
                samplesToProcess -= self.samplesPerBuffer
                start += self.samplesPerBuffer
        print("Freeing buffers... ", end="")
        for buf in self.buffers:
            buf.__exit__()
        self.buffers = []
        print('done.')
        return True

    def abort(self):
        print("aborting! ... ")
        # While aborting, wait_acquisition_complete raises nothing, so an abort never
        # reports the acquisition's exception.
        self.aborting = True
        self.wait_acquisition_complete()
        self.aborting = False
        print("abort complete.")
        return True

    def abort_buffered(self):
        print("abort_buffered: ...")
        return self.abort()

    def abort_transition_to_buffered(self):
        print("abort_transition_to_buffered: ...")
        return self.abort()

    def shutdown(self):
        if self.aborting:
            print('Shutdown requested during abort; waiting 10 seconds.')
            start = time.perf_counter()
            while self.aborting and time.perf_counter() - start < 10:
                time.sleep(0.5)
        if self.aborting:
            print('Proceeding in lieu of complete abort.')
        return


# labscript_devices.AlazarTechBoard.GuilessWorker is this board's worker.
GuilessWorker = AlazarTechBoardWorker
