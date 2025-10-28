from apsbits.core.instrument_init import oregistry


def undulator_setup(ds='N',ds_off=999,ds_harm=0,us='N',us_off=999,us_harm=0):
    """
    Select undulators used and turn energy tracking on/off

    - Undulator offset denotes difference of undulator energy to monochromator energy
      - [c]alculate: calculates offset from monochromator and undulator current energies


    """

    undulators = oregistry.find("undulators")
    energy = oregistry.find("energy")

    ds_inq = False
    us_inq = False
    ds_off_inq = False
    us_off_inq = False
    if ds != 'N':
        ds_inq = True
    elif ds == 'N' and undulators.ds.tracking.get():
        ds = 'Y'
        ds_inq = False
    else:
        ds_inq = False
        
    if us != 'N':
        us_inq = True
    elif us == 'N' and undulators.us.tracking.get():
        us = 'Y'
        us_inq = False
    else:
        us_inq = False
        
    
    if undulators.ds.energy_offset.get()==0 and ds_off==999:
        ds_off = undulators.ds.energy.readback.get()-energy.get()
    elif ds_off==999:
        ds_off = undulators.ds.energy_offset.get()
    else:
        ds_off_inq = True
    if undulators.us.energy_offset.get()==0 and us_off==999:
        us_off = undulators.us.energy.readback.get()-energy.get()
    elif us_off==999:
        us_off = undulators.us.energy_offset.get()
    else:
        us_off_inq = True

    if ds_harm == 0: 
        ds_harm = undulators.ds.harmonic_value.get()    
        ds_harm_inq = False
    else:
        ds_harm_inq = True
        
    if us_harm == 0: 
        us_harm = undulators.us.harmonic_value.get()    
        us_harm_inq = False
    else:
        us_harm_inq = True



    ds = (
        ds if ds_inq
        else input(f"Use DS undulator [{ds}]: ") or ds
    )
    if ds in ['Yes','Y','y','yes']:
        ds_off = (
            ds_off if ds_off_inq
            else input(f"   DS undulator offset (value/[c]alculate) [{ds_off:.3f}]: ") or ds_off
            )
        if ds_off == 'c':
            ds_off = undulators.ds.energy.readback.get()-energy.get()
        ds_harm = (
            ds_harm if ds_harm_inq
            else input(f"   DS undulator harmonics (1,3,5,../[c]alculate) [{ds_harm:.0f}]: ") or ds_harm
        )
        if ds_harm == 'c':
            en = energy.get()
            if en < 8.6:
                ds_harm = 1 
            elif en < 18:
                ds_harm = 3
            else:
                ds_harm = 5
                
            
        undulators.ds.energy_offset.put(float(ds_off))
        undulators.ds.tracking.put(True)       
        try:
            if ds_harm in [1,3,5,7,9]:
                undulators.ds.harmonic_value.put(int(ds_harm))
                print(f"Undulator uses harmonic {ds_harm:.0f}")
            else:
                print("     Harmonics needs to be an odd integer!")
        except:
            print("     Undulator currently disabled")
        print(f"DS undulator tracking with offset = {float(ds_off):.3f}\n")
    else:
        undulators.ds.tracking.put(False)
        print(f"DS undulator tracking OFF\n")

    us = (
        us if us_inq
        else input(f"Use US undulator [{us}]: ") or us
    )
    if us in ['Yes','Y','y','yes']:
        us_off = (
            us_off if us_off_inq
            else input(f"   US undulator offset (value/[c]alculate) [{us_off:.3f}]: ") or us_off
            )
        if us_off == 'c':
            us_off = undulators.us.energy.readback.get()-energy.get()
        us_harm = (
            us_harm if us_harm_inq
            else input(f"   US undulator harmonics (1,3,5,../[c]alculate) [{us_harm:.0f}]: ") or us_harm
        )
        if us_harm == 'c':
            en = energy.get()
            if en < 8.6:
                ds_harm = 1 
            elif en < 18:
                ds_harm = 3
            else:
                ds_harm = 5
        undulators.us.energy_offset.put(float(us_off))
        undulators.us.tracking.put(True)
        try:
            if us_harm in [1,3,5,7,9]:
                undulators.us.harmonic_value.put(int(us_harm))
                print(f"Undulator uses harmonic {us_harm:.0f}")
            else:
                print("     Harmonics needs to be an odd integer!")
        except:
            print("     Undulator currently disabled")
        print(f"US undulator tracking with offset = {float(us_off):.3f}")
    else:
        undulators.us.tracking.put(False)
        print(f"US undulator tracking OFF")
       
        
