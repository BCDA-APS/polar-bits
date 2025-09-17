from apsbits.core.instrument_init import oregistry
from pyRestTable import Table


def get_devices(label):
    """
    Prints a table with the devices that have the label.

    Parameters
    ----------
    label : str
        Label to be searched. This will be something like "scaler".

    Returns
    -------
    None

    See also
    --------
    :func:`ophydregistry.Registry.findall`
    """

    objs = oregistry.findall(label=label, allow_none=True)
    objs.sort(key=lambda x: x.name)  # Sort by name
    table = {"Ophyd name": [], "PV prefix": [], "Label": []}
    for obj in objs:
        table["Ophyd name"].append(obj.name)
        if getattr(obj, "prefix", None):
            table["PV prefix"].append(obj.prefix)
        else:
            table["PV prefix"].append("-None-")
        table["Label"].append(obj._ophyd_labels_)

    print(Table(table).reST(fmt="grid"))
