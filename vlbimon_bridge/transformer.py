import sys
import re
from collections import defaultdict
import json

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

    return stations


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
    # telescope_onSource handled below
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

            if param == 'telescope_observingMode':
                # SMA sends a mode of ' ' whenever it goes off source
                if value.isspace():
                    value = ''

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


def init_station_status(stations, verbose=0):
    station_status = {}
    for s in stations:
        ss = {}
        for key in ('source', 'mode', 'onsource'):
            ss[key] = ''
        ss['time'] = 0
        ss['station'] = s
        station_status[s] = ss

    if verbose > 1:
        print('init station status')
        print(json.dumps(station_status, sort_keys=True, indent=4))
    return station_status


def update_station_status(station_status, tables, verbose=0):
    changed = set()

    for point in tables.get('telescope_telescope_sourceName', []):
        recv_time, station, value = point
        if value.isspace():  # SMA sends a ' ' when it goes off source
            value = ''
        station_status[station]['source'] = value
        changed.add(station)

    for point in tables.get('telescope_observingMode', []):
        recv_time, station, value = point
        station_status[station]['mode'] = value
        changed.add(station)

    for point in tables.get('telescope_onSource', []):
        recv_time, station, value = point
        source = station_status[station]['source']
        if value:
            v = 'on'
            # this is trying to be a bit too clever... hard to be sure that time ordering is correct
            #if recv_time > station_status[station]['time'] and source and source.startswith('was '):
            #    station_status[station]['source'] = source
        else:
            v = 'off'
            #if recv_time > station_status[station]['time'] and source and not source.startswith('was '):
            #    station_status[station]['source'] = 'was ' + source
        station_status[station]['onsource'] = v
        changed.add(station)

    status_table = []
    for station in changed:
        if verbose > 1:
            print('station', station, 'has changed')
            print(json.dumps(station_status[station], sort_keys=True, indent=4))
        station_status[station]['time'] = recv_time
        status_table.append([station_status[station][k] for k in ('time', 'station', 'source', 'onsource', 'mode')])

    if verbose > 1:
        print('station status')
        for row in status_table:
            print(row)

    return status_table
