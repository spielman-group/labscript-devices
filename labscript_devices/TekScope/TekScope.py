import pyvisa
import numpy as np
import time


class TekScope:
    """The VISA interface to a Tektronix oscilloscope, which TekScopeWorker drives."""

    def __init__(self, addr='USB?*::INSTR',
                 timeout=1, termination='\n'):
        rm = pyvisa.ResourceManager()
        devs = rm.list_resources(addr)
        assert len(devs), (
            f"pyvisa found no connected devices matching {addr}. Check that the scope "
            "is connected and that addr matches its VISA address."
        )
        # The first resource matching addr is the one opened.
        self.dev = rm.open_resource(devs[0])
        # pyvisa's timeout is in milliseconds; this one is in seconds.
        self.dev.timeout = 1000 * timeout
        self.dev.read_termination = termination
        self.idn = self.dev.query('*IDN?')
        self.read = self.dev.read
        self.write = self.dev.write
        self.query = self.dev.query

    def channels(self, all=True):
        """Return {channel: displayed}, REF and MATH included if the scope has them.

        Only the displayed channels if `all` is False.
        """
        # want to enable HEAD to get channel names as well
        prev = self.dev.query('HEAD?')
        self.dev.write('HEAD 1')

        # determine the device capabilities and enabled status
        resp = self.dev.query('SEL?').rsplit(':',1)[1]

        self.dev.write('HEAD '+prev)

        vals = {}
        for x in resp.split(';'):
            name, val = x.rsplit(' ',1)
            if name[0] == ':':
                name = name.rsplit(':',1)[1]
            try:
                visible = bool(int(val))
            except:
                continue
            if all or visible:
                vals[name] = visible
        return vals

    def waveform(self, channel='CH1', preamble_string='WFMO', int16=False):
        """Return the preamble dict, times and values of the whole record of `channel`."""
        # set the location of the data transferred by CURVe?
        self.dev.write('DAT:SOU ' + channel)
        # transfer the waveform in binary format (signed, MSB)
        self.dev.write('DAT:ENC RIB')
        if int16:
            # use 16-bit integers
            self.dev.write(preamble_string + ':BYT_N 2')
        else:
            # use 8-bit integers
            self.dev.write(preamble_string + ':BYT_N 1')
        # determine how many points exist: all acquired points are downloaded, as set
        # by the 'Record length' setting in the 'Acquisition' menu
        record_length = int(self.dev.query('HOR:RECO?'))
        # set the first data point to transfer
        self.dev.write('DAT:START ' + '1')
        # set the last data point to transfer
        self.dev.write('DAT:STOP ' + str(record_length))

        raw = self.dev.query_binary_values('CURV?',
            datatype='h' if int16 else 'b',
            is_big_endian=True,
            container=np.array
            )

        # the fields of the waveform preamble
        keys = [
            'BYT_NR',                                 # data width for the outgoing waveform
            'BIT_NR',                                 # number of bits per waveform point (8 or 16)
            'ENCDG',                                  # type of encoding (ASCII or binary)
            'BN_FMT',                                 # format of binary data (redundant for ASCII transfer)
            'BYT_OR',                                 # first transmitted byte of binary data (LSB or MSB)
            'NR_PT',                                  # number of points transmitted in response to a CURVe? query
            'WFID',                                   # acquisition parameters
            'PT_FMT',                                 # point format: {ENV: min/max pairs, Y: single points}
            'XINCR',                                  # horizontal increment
            'PT_OFF',                                 # trigger offset
            'XZERO',                                  # time coordinate of the first point
            'XUNIT',                                  # horizontal units
            'YMULT',                                  # vertical scale factor per digitizing level
            'YZERO',                                  # vertical offset
            'YOFF',                                   # vertical position in digitizing levels
            'YUNIT'                                   # vertical units
            ]

        # One query for every field, answered as their values separated by ';'.
        self.dev.write(';:'.join([preamble_string + ':' + k  + '?' for k in keys]))
        wfstr = self.dev.read().split(';')

        # A quoted value loses its quotes; any other becomes an int or a float if it can.
        wfmp = {}
        for key, x in zip(keys, wfstr):
            x = str(x)
            if x[0] == '"':
                x = x.split('"')[1]
            elif str.isdigit(x):
                x = int(x)
            else:
                try: x = float(x)
                except: pass
            wfmp[key] = x

        n = np.arange(wfmp['NR_PT'])
        t = wfmp['XINCR'] * (n - wfmp['PT_OFF']) + wfmp['XZERO']
        y = wfmp['YMULT'] * (raw - wfmp['YOFF']) + wfmp['YZERO']
        return wfmp, t, y

    def get_screenshot(self, verbose=False):
        if verbose:
            print('Downloading screen image...')
        self.dev.write('SAVE:IMAG:FILEF PNG')
        self.dev.write('HARDCOPY START')
        return self.dev.read_raw(None)

    def save_screenshot(self, filepath, verbose=False):
        if verbose:
            print('Saving screen image...')
        data = self.get_screenshot()
        with open(filepath, 'wb') as f:
            f.write(data)

    def set_date_time(self, verbose=False):
        if verbose:
            print('Setting date and time...')
        self.dev.write('DATE "' + time.strftime('%Y-%m-%d',time.localtime()) + '"')
        self.dev.write('TIME "' + time.strftime('%H:%M:%S',time.localtime()) + '"')

    def lock(self, verbose=False):
        if verbose:
            print('Locking front panel')
        self.dev.write('LOCk ALL')

    def unlock(self, verbose=False):
        if verbose:
            print('Unlocking front panel')
        self.dev.write('LOCk NONE')

    def get_acquire_state(self):
        response = self.dev.query('ACQ:STATE?')
        return int(response)

    def set_acquire_state(self, running=True):
        self.dev.write('ACQ:STATE ' + ('START' if running else 'STOP'))

    def close(self):
        self.dev.close()
