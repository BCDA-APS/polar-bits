"""Eiger geometry setup: sample-detector distance and beam center."""

from apsbits.core.instrument_init import oregistry
from epics import caput

#: Beam center (x, y) array on the 4-ID-G soft IOC; not an Eiger PV.
CENTER_PV = "4idgSoftX:Eiger:Center"


def setup_eiger():
    """
    Write the sample-detector distance and beam center to the Eiger.

    The distance defaults to the current position of the ``huber_euler`` pad
    rail. The beam center is taken as the center of ROI1.

    The soft-IOC beam center array is not part of the ADEiger driver, so it
    is written with a raw ``caput`` rather than an ophyd signal.
    """
    eiger = oregistry.find("eiger")
    pad_rail = oregistry.find("huber_euler").pad_rail

    distance = pad_rail.user_readback.get()
    answer = input(f"sample - detector distance: [{distance}]? ")
    if answer.strip():
        distance = float(answer)
    eiger.cam.det_distance.set(distance).wait(timeout=10)

    roi = eiger.roi1
    eiger_x = roi.min_xyz.min_x.get() + roi.size.x.get() / 2
    eiger_y = roi.min_xyz.min_y.get() + roi.size.y.get() / 2
    caput(CENTER_PV, [eiger_x, eiger_y])
    eiger.cam.beam_center_x.set(eiger_x).wait(timeout=10)
    eiger.cam.beam_center_y.set(eiger_y).wait(timeout=10)
    print(f"Eiger beam (x,y) = {(eiger_x, eiger_y)}")
