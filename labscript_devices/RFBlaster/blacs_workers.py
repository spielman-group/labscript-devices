#####################################################################
#                                                                   #
# /labscript_devices/RFBlaster/blacs_workers.py                     #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript_devices.common.deadline import Deadline
from labscript_devices.common.pseudoclock import PseudoclockWorker
from labscript_utils.setup_logging import setup_logging


class MultiPartForm:
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))

    def add_file_content(self, fieldname, filename, body, mimetype=None):
        import mimetypes
        if not isinstance(body, bytes):
            raise TypeError('body must be bytes')
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))


class RFBlasterWorker(PseudoclockWorker):
    def init(self):
        exec('from numpy import *', globals())
        global h5py; import labscript_utils.h5_lock, h5py
        global re; import re
        # Seconds the RFBlaster has to answer an HTTP request.
        self.timeout = 10
        p = re.compile('http://([0-9.]+):[0-9]+')
        m = p.match(self.address)
        self.ip = m.group(1)
        self.netlogger = setup_logging(f'rfBlaster_{self.ip}')
        self.netlogger.info('init: Started logging')
        # See if the RFBlaster answers
        self.http_request()
        self._last_program_manual_values = {}

    def program_manual(self, front_panel_values):
        self._last_program_manual_values = front_panel_values
        form = MultiPartForm()
        for i in range(self.num_DDS):
            # The board takes the amplitude in % and the frequency in MHz.
            form.add_field(
                f"a_ch{i}_in",
                str(
                    100*front_panel_values[f'dds {i}']['amp']
                    * front_panel_values[f'dds {i}']['gate']
                ),
            )
            form.add_field(f"f_ch{i}_in", str(front_panel_values[f'dds {i}']['freq']*1e-6))
            form.add_field(f"p_ch{i}_in", str(front_panel_values[f'dds {i}']['phase']))
        form.add_field("set_dds", "Set device")
        return_vals = self.get_web_values(self.http_request(form))
        return return_vals

    def transition_to_buffered(self, device_name, h5_file, front_panel_values, fresh):
        with h5py.File(h5_file, 'r') as hdf5_file:
            group = hdf5_file['devices'][device_name]
            # The form carries each DDS's binary program, and is posted below.
            form = MultiPartForm()
            self.final_values = {}
            for i in range(self.num_DDS):
                # The front panel's final values are the last row of TABLE_DATA, the
                # table before quantising.
                self.final_values[f'dds {i}'] = {'freq': group['TABLE_DATA'][f"freq{i}"][-1],
                                                 'amp': group['TABLE_DATA'][f"amp{i}"][-1],
                                                 'phase': group['TABLE_DATA'][f"phase{i}"][-1],
                                                 'gate': True
                                                }
                data = group[f'BINARY_CODE/DDS{i}'][()]
                form.add_file_content(f"pulse_ch{i}", f"output_ch{i}.bin", data)

        form.add_field("upload_and_run", "Upload and start")
        self.http_request(form)
        return self.final_values

    def abort(self):
        form = MultiPartForm()
        form.add_field("halt", "Halt execution")
        self.http_request(form)
        return True

    def abort_transition_to_buffered(self):
        return self.abort()

    def abort_buffered(self):
        return self.abort()

    def transition_to_manual(self):
        # The RFBlaster cannot say whether its program has finished, so this takes
        # shot_finished's default, True.
        self.wait_for_end_of_shot()
        return True

    def http_request(self, form=None):
        """Fetch the board's page, or post `form` to it, and return the page's text."""
        import requests
        from urllib3.exceptions import ReadTimeoutError

        deadline = Deadline(self.device_name, 'answer an HTTP request', self.timeout)
        with deadline.timeout_for(requests.exceptions.Timeout, TimeoutError) as timeout:
            try:
                if form is not None:
                    # requests takes form_fields, a list of (key, value) tuples, as it
                    # is, but wants each file as (field name, (filename, body, type)).
                    filelist = [
                        (field_name, (filename, bytes(body), content_type))
                        for field_name, filename, content_type, body in form.files
                    ]
                    r = requests.post(
                        self.address, data=form.form_fields, files=filelist, timeout=timeout
                    )
                else:
                    r = requests.get(self.address, timeout=timeout)
            except requests.exceptions.ConnectionError as e:
                # requests reports a timeout while reading the body as a ConnectionError
                if e.args and isinstance(e.args[0], ReadTimeoutError):
                    raise TimeoutError from e
                raise
        r.raise_for_status()
        self.netlogger.info('Connected!')
        return r.text

    def get_web_values(self, page):
        import re
        search = re.compile(r'name="([fap])_ch(\d+?)_in"\s*?value="([0-9.]+?)"')
        webvalues = re.findall(search, page)

        register_name_map = {'f': 'freq', 'a': 'amp', 'p': 'phase'}
        newvals = {}
        for i in range(self.num_DDS):
            newvals[f'dds {i}'] = {}
        for register, channel, value in webvalues:
            newvals[f'dds {int(channel)}'][register_name_map[register]] = float(value)
        for i in range(self.num_DDS):
            if f'dds {i}' in self._last_program_manual_values and newvals[f'dds {i}']['amp'] == 0:
                newvals[f'dds {i}']['gate'] = self._last_program_manual_values[f'dds {i}']['gate']
            else:
                newvals[f'dds {i}']['gate'] = True

            # BLACS takes the frequency in Hz and the amplitude as a fraction of full scale.
            newvals[f'dds {i}']['freq'] *= 1e6
            newvals[f'dds {i}']['amp'] /= 100

            # If the gate is off, keep the front panel amplitude.
            if not newvals[f'dds {i}']['gate']:
                newvals[f'dds {i}']['amp'] = self._last_program_manual_values[f'dds {i}']['amp']

        return newvals

    def check_remote_values(self):
        # Read the webserver page to see what values it puts in the form
        return self.get_web_values(self.http_request())

    def shutdown(self):
        pass
