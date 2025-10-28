from polartools.load_data import load_catalog
from apsbits.core.instrument_init import oregistry
from ..plans.center_maximum import cen, maxi
from datetime import datetime

def opt(method='cen'):
	"""
    Move positioner of last scan to center of last scan    

    usage: RE(opt())
	optional argument: 	method = 'cen' (default)
						method = 'max'


    """
	cat = load_catalog("4id_polar")
	motor = cat[-1].metadata["start"]
	rmotor = '.'.join(motor["motors"][0].rsplit('_',1))
	positioner = oregistry.find(motor["motors"][0])
	time = datetime.now()-datetime.fromtimestamp(motor['time'])

	if time.seconds<60:
		if method == 'cen':
			yield from cen(positioner)
		elif method == 'max':
			yield from maxi(positioner)

	else:
		inp = input(f"Move {rmotor} to center (Y/[N])? " )
		if inp in ['Y','y','yes']:
			if method == 'cen':
				yield from cen(positioner)
			elif method == 'max':
				yield from maxi(positioner)
