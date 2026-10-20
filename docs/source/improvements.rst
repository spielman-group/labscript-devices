Possible improvements
=====================

Improvements judged worth making, but larger than a small change.

* **The values a manual program took.** NI_DAQmx's and the PulseBlasters' ``program_manual`` return nothing, so BLACS shows the values asked for, not the ones the hardware took after quantising.
* **Connections checked when they are made.** A PulseBlaster checks its outputs' connections, and that a board without DDS has no DDS on it, only when the shot compiles; an AlazarTechBoard does not check its inputs' connections at all. Checking in ``add_device`` would put the error at the line that connects.
* **Measured delays.** The PineBlaster's ``wait_delay``, the RFBlaster's ``trigger_delay`` and ``wait_delay``, and the CiceroOpalKellyXEM3001's ``trigger_delay`` and ``wait_delay`` are estimates. Measuring each on a board would make the timing exact.
* **Andor acquisitions.** The AndorSolis worker waits for the camera to go idle, with a timeout. Counting the frames acquired would end the wait sooner, and checking for an abort during it would make an abort prompt.
* **TekScope settings per shot.** The TekScope worker fixes the acquisition mode and channels; the shot file could give them.
* **Waits close together.** A pseudoclock's BLACS tab polls the board's status every 100 ms, and the CiceroOpalKellyXEM3001 finds its waits from sample counts, so two waits closer than a poll can be taken for one.
* **Reporting a worker's failure.** A pseudoclock's BLACS tab tells BLACS that a shot failed by faking a restart of the device. A BLACS call for it would be plainer.
* **Front-panel bit packing.** NI_DAQmx's worker and runviewer parser, and the PrawnDO's worker, each pack a port's line values into an integer and back. One helper beside labscript's ``bitfield`` could serve all three.
* **TekScope's module name.** The driver module ``TekScope/TekScope.py`` has the class's name, so once a worker imports it, ``labscript_devices.TekScope.TekScope`` is the module, not the class. Renaming the module would end that.
* **test_device's keyword.** ``DoSomething`` would be ``do_something``, with the old name kept as a legacy keyword.
