from epics import caget
from epics import caput

def setup_eiger():
    """
    Setup and write parameters to Eiger images

    Parameters
    ----------

    """
    _geom_ = get_diffractometer()
    _geom_for_psi_ = oregistry.find(_geom_.name + "_psi")

    sample = _geom_.sample

    eiger_distance = caget("4idgSoft:m21.RBV")
    eiger_distance = input(
        f"sample - detector distance: [{eiger_distance}]? " or eiger_distance
    )
    caput("4idEiger:cam1:DetDist", eiger_distance)
    eiger_x = caget("4idEiger:ROI1:MinX") + caget("4idEiger:ROI1:SizeX")/2
    eiger_y = caget("4idEiger:ROI1:MinY") + caget("4idEiger:ROI1:SizeY")/2
    caput("4idgSoftX:Eiger:Center", [eiger_x,eiger_y])
    caput("4idEiger:cam1:BeamX_RBV", eiger_x)
    caput("4idEiger:cam1:BeamY_RBV", eiger_y)
    print(f"Eiger beam (x,y) = {(eiger_x/eiger_y)}")
