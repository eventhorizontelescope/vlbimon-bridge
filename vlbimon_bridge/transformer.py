import sys
import re

from . import utils

splitters = []
telescope_events = []


def init(verbose=0):
    stations, parameters = utils.read_masterlist()

    for p, v in parameters.items():
        if 'datatype' in v and v['datatype'] == 'CelestialCoordinates':
            splitters.append(p)
        if p.startswith('telescope_') and 'datatype' in v and v['datatype'] == 'string':
            telescope_events.append(p)
        if p.startswith('observerMessages_') and 'datatype' in v and v['datatype'] == 'string':
            telescope_events.append(p)
    telescope_events.append('telescope_onSource')  # a bool

    if verbose:
        print('splitters:', *splitters, file=sys.stderr)
        print('events:', *telescope_events, file=sys.stderr)


def transform(flat, verbose=0):
    flat = transform_events(flat, verbose=verbose)
    flat = transform_split_coords(flat, verbose=verbose)
    return flat


event_map = {
    'telescope_sourceName': 'source name is',
    'telescope_observingMode': 'mode is',
    'telescope_pointingCorrection': 'pointing is',
    'telescope_focusCorrection': 'focus is',
    'observerMessages_observer': 'observer is',
    'observerMessages_observatoryStatus': 'status is',
    'observerMessages_weather': 'weather is',
}


def transform_events(flat, verbose=0):
    extras = []
    for f in flat:
        station, param, recv_time, value = f
        if param in telescope_events:
            if param == 'telescope_onSource':
                if value == 'true':
                    event = 'is on source'
                else:
                    event = 'is off source'
            elif param in event_map:
                event = event_map[param] + ' ' + value
            extras.append([station, 'events', recv_time, event])
    if verbose:
        print('events', file=sys.stderr)
        [print(e, file=sys.stderr) for e in extras]
    return flat + extras
        

def transform_split_coords(flat, verbose=0):
    extras = []
    for f in flat:
        station, param, recv_time, value = f
        if param in splitters:
            # might have a leading minus, might have a leading plus
            m = re.match(r'([+\-]?[0-9.]+)([+\-]?[0-9.]+)', value)
            if not m:
                print('failed to split', station, param, value, file=sys.stderr)
                continue
            ra, dec = m.groups()
            if param == 'telescope_azimuthElevation':
                suffix = ('_az', '_alt')
            else:
                suffix = ('_ra', '_dec')
            extras.append([station, param+suffix[0], recv_time, ra])
            extras.append([station, param+suffix[1], recv_time, dec])
    if verbose:
        print('splits', file=sys.stderr)
        [print(e, file=sys.stderr) for e in extras]
    return flat + extras
