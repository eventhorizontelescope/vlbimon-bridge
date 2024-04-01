import sys
import re
from collections import defaultdict
import json

from . import utils
from . import sqlite

splitters = []
splitters_map = {}
splitters_expanded = []  # used by sqlite.initdb(), assumed to be 'REAL'
telescope_events = []


def init(verbose=0):
    stations, parameters = utils.read_masterlist()

    for p, v in parameters.items():
        if 'datatype' in v and v['datatype'] in {'CelestialCoordinates', 'AzElCoordinates'}:
            splitters.append(p)
            e = splitters_names(p, v['datatype'])
            splitters_expanded.extend(e)
            splitters_map[p] = e
        if p.startswith('telescope_') and 'datatype' in v and v['datatype'] == 'string':
            telescope_events.append(p)
        if p.startswith('observerMessages_') and 'datatype' in v and v['datatype'] == 'string':
            telescope_events.append(p)
    telescope_events.append('telescope_onSource')  # a bool
    # Tsys and tau225 do not generate events

    if verbose:
        print('splitters:', *splitters, file=sys.stderr)
        print('events:', *telescope_events, file=sys.stderr)

    return stations


def splitters_names(param, datatype):
    if datatype == 'AzElCoordinates':
        suffix = ('_az', '_el')
    elif datatype == 'CelestialCoordinates':
        suffix = ('_ra', '_dec')
    else:
        raise ValueError('do not know how to split '+param)
    return (param + suffix[0], param + suffix[1])


def transform(flat, verbose=0, dedup_events=False):
    flat = transform_events(flat, verbose=verbose, dedup_events=dedup_events)
    flat = transform_splitters(flat, verbose=verbose)
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


# used to dedup
station_latest_event = defaultdict(dict)


def onsource(value):
    if isinstance(value, str):
        if value in {'true', 'True'}:  # I have only seen 'true'
            return 'on'
        elif value in {'false', 'False'}:  # I have only seen 'False'
            return 'off'
    elif isinstance(value, bool):  # KP, SMTO
        if value:
            return 'on'
        else:
            return 'off'

    print('no idea what onsource value', repr(value), 'means')
    return 'off'


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

            if param == 'telescope_epochType':
                continue

            if param == 'telescope_observingMode':
                # SMA sends a mode of ' ' whenever it goes off source
                if value.isspace():
                    value = ''

            if param == 'telescope_onSource':
                if onsource(value):
                    event = 'is on source'
                else:
                    event = 'is off source'
            elif param in event_map:
                event = event_map[param] + ' ' + value
            else:
                p = param.replace('observerMessages_', '')
                p = param.replace('telescope_', '')
                event = p + ' is ' + value

            extras.append([station, 'events', recv_time, station + ' ' + event])
    if verbose > 1:
        print('events:', file=sys.stderr)
        [print(' ', e, file=sys.stderr) for e in extras]
    return flat + extras


def transform_splitters(flat, verbose=0):
    extras = []
    for f in flat:
        station, param, recv_time, value = f
        if param in splitters:
            # might have a leading minus, might have a leading plus
            m = re.match(r'([+\-]?[0-9.]+)([+\-]?[0-9.]+)', value)
            if not m:
                print('failed to split', station, param, value, file=sys.stderr)
                continue
            first, second = m.groups()
            expanded = splitters_map[param]
            extras.append([station, expanded[0], recv_time, first])
            extras.append([station, expanded[1], recv_time, second])
    if verbose > 1:
        print('splits:', file=sys.stderr)
        [print(' ', e, file=sys.stderr) for e in extras]
    return flat + extras


def init_station_status(con, stations, verbose=0):
    '''Initialize the station status to a valid state, and then try to read it out of the database.'''
    station_status = {}

    # the order here must match the order in sqlite.station_status_cols
    for s in stations:
        ss = {}
        for key in ('source', 'mode', 'onsource'):
            ss[key] = ''
        ss['time'] = 0
        ss['station'] = s
        ss['recording'] = '....'
        ss['tsys'] = 0.  # should this be NaN? PICO currently never sets it.
        ss['tau225'] = 0.  # should this be NaN?
        ss['scan'] = ''

        station_status[s] = ss

    if verbose > 1:
        print('init station status:')
        print(' ', json.dumps(station_status, sort_keys=True, indent=4))

    rows = sqlite.get_station_status(con)
    changed = set()
    for r in rows:
        station = r['station']
        if station not in station_status:
            print('ignoring readback of unknown station', station)
            continue
        changed.add(station)
        for k in r.keys():
            if k == 'station':
                continue
            if k == 'recording':
                if len(r[k]) != 4:
                    continue
            station_status[station][k] = r[k]

    if verbose > 1:
        print('restored station status')
        for k, v in station_status.items():
            if k not in changed:
                continue
            print(' ', json.dumps(station_status[k], sort_keys=True))

    for station in station_status:
        if verbose > 1:
            print('station_status', len(station_status[station]))
            print('station_status_cols', len(sqlite.station_status_cols))
        assert len(station_status[station]) == len(sqlite.station_status_cols)

    return station_status


recorder_map = {
    'recorder_1_shouldRecord': 1,
    'recorder_2_shouldRecord': 2,
    'recorder_3_shouldRecord': 3,
    'recorder_4_shouldRecord': 4,
}

extra_status_map = {
    'if_1_systemTemp': 'tsys',
    'weather_tau225': 'tau225',
}

status_table_cols = ('time', 'station', 'source', 'onsource', 'mode', 'recording', 'tsys', 'tau225')


def recording_set_or_unset(old_value, param, value):
    recorder = recorder_map[param]  # recorder is an integer 1..4
    by = bytearray(old_value, encoding='utf8')
    if value:
        letter = ord('0') + recorder
    else:
        letter = ord('.')
    by[recorder-1] = letter
    return by.decode('utf8')


def station_change(station_status, changed, param, recv_time, station, value):
        station_status[station][param] = value
        changed.add(station)
        old = station_status[station]['time']
        if recv_time > old:
            # we don't process the points in time order, don't set the clock backwards
            station_status[station]['time'] = recv_time


def update_station_status(station_status, tables, verbose=0):
    changed = set()

    for point in tables.get('telescope_sourceName', []):
        recv_time, station, value = point
        if value.isspace():  # SMA sends a ' ' when it goes off source
            value = ''
        station_change(station_status, changed, 'source', recv_time, station, value)

    for point in tables.get('telescope_observingMode', []):
        recv_time, station, value = point
        station_change(station_status, changed, 'mode', recv_time, station, value)

    for point in tables.get('telescope_onSource', []):
        recv_time, station, value = point
        value = onsource(value)
        station_change(station_status, changed, 'onsource', recv_time, station, value)

    for param in recorder_map.keys():
        for point in tables.get(param, []):
            recv_time, station, value = point
            old_value = station_status[station]['recording']
            value = recording_set_or_unset(old_value, param, value)
            station_change(station_status, changed, 'recording', recv_time, station, value)

    for param, translation in extra_status_map.items():
        for point in tables.get(param, []):
            recv_time, station, value = point
            station_change(station_status, changed, translation, recv_time, station, value)

    status_table = []
    for station in changed:
        if verbose:
            print('station', station, 'has changed')
            print(json.dumps(station_status[station], indent=4))  # no sort_keys=True because it's an ordered dict

        cols = [p[0] for p in sqlite.station_status_cols]
        # these all exist because of init_station_status()
        status_table.append([station_status[station][p] for p in cols])

    return status_table
