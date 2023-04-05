import sys
import re
from collections import defaultdict

from . import utils

splitters = []
splitters_expanded = []
telescope_events = []


def init(verbose=0):
    stations, parameters = utils.read_masterlist()

    for p, v in parameters.items():
        if 'datatype' in v and v['datatype'] in {'CelestialCoordinates', 'AzElCoordinates'}:
            splitters.append(p)
        if p.startswith('telescope_') and 'datatype' in v and v['datatype'] == 'string':
            telescope_events.append(p)
        if p.startswith('observerMessages_') and 'datatype' in v and v['datatype'] == 'string':
            telescope_events.append(p)
    telescope_events.append('telescope_onSource')  # a bool

    for s in splitters:
        splitters_expanded.extend(expand_ra_dec(s))

    if verbose:
        print('splitters:', *splitters, file=sys.stderr)
        print('events:', *telescope_events, file=sys.stderr)


def expand_ra_dec(param):
    if param == 'telescope_azimuthElevation':
        suffix = ('_az', '_alt')
    else:
        suffix = ('_ra', '_dec')
    return (param + suffix[0], param + suffix[1])


def transform(flat, verbose=0, dedup_events=False):
    flat = transform_events(flat, verbose=verbose, dedup_events=dedup_events)
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


station_latest_event = defaultdict(dict)


def transform_events(flat, verbose=0, dedup_events=False):
    extras = []
    for f in flat:
        station, param, recv_time, value = f
        if param in telescope_events:
            if dedup_events and station_latest_event[station].get(param) == value:
                if verbose:
                    print('deduping event', station, param, value)
                continue
            station_latest_event[station][param] = value

            if param == 'telescope_onSource':
                # this can be a string or a bool
                if isinstance(value, str) and value in {'true', 'True'}:  # I have only seen 'true'
                    event = 'is on source'
                elif isinstance(value, bool) and value:  # KP, SMTO
                    event = 'is on source'
                else:
                    event = 'is off source'
            elif param in event_map:
                event = event_map[param] + ' ' + value
            else:
                # default formatting. we might want to suppress things like telescope_epochType
                p = param.replace('telescope_', '')
                event = p + ' is ' + value

            extras.append([station, 'events', recv_time, station + ' ' + event])
    if verbose > 1:
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
            expanded = expand_ra_dec(param)
            extras.append([station, expanded[0], recv_time, ra])
            extras.append([station, expanded[1], recv_time, dec])
    if verbose > 1:
        print('splits', file=sys.stderr)
        [print(e, file=sys.stderr) for e in extras]
    return flat + extras
