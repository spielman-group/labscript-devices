Possible improvements
=====================

Improvements judged worth making, but larger than a small change.

* **The values a manual program took.** NI_DAQmx's and the PulseBlasters' ``program_manual`` return nothing, so BLACS shows the values asked for, not the ones the hardware took after quantising.
* **Connections checked when they are made.** A PulseBlaster checks its outputs' connections, and that a board without DDS has no DDS on it, only when the shot compiles; an AlazarTechBoard does not check its inputs' connections at all. Checking in ``add_device`` would put the error at the line that connects.
* **Measured delays.** The PineBlaster's ``wait_delay``, the RFBlaster's ``trigger_delay`` and ``wait_delay``, and the CiceroOpalKellyXEM3001's ``trigger_delay`` and ``wait_delay`` are estimates. Measuring each on a board would make the timing exact.
* **Andor acquisitions.** The AndorSolis worker waits for the camera to go idle, and when its timeout runs out it stops waiting and downloads what there is. It could instead end the wait once the expected frames have arrived, and on a timeout keep waiting unless the shot is aborted.
* **TekScope settings per shot.** The TekScope worker fixes the acquisition mode and stop condition, and downloads whichever channels the scope displays; the shot file could give both.
* **Waits close together.** A pseudoclock's BLACS tab polls the board's status every 100 ms, and the CiceroOpalKellyXEM3001 finds its waits from sample counts between polls, so a shot with two waits closer than a poll fails, saying a wait came too soon after another.
* **Reporting a worker's failure.** A pseudoclock's BLACS tab tells BLACS that a shot failed by faking a restart of the device. A BLACS call for it would be plainer.
* **Front-panel bit packing.** NI_DAQmx's worker packs a port's line values into an integer and unpacks them, its runviewer parser unpacks them, and the PrawnDO's worker does both. One helper beside labscript's ``bitfield`` could serve all three.
* **TekScope's module name.** The driver module ``TekScope/TekScope.py`` has the class's name, so once a worker imports it, ``labscript_devices.TekScope.TekScope`` is the module, not the class. Renaming the module would end that.
* **test_device's keyword.** ``DoSomething`` would be ``do_something``, with the old name kept as a legacy keyword.
