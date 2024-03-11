import os
import os.path
import sys
import grp
import json
import time
from collections import defaultdict
import numpy as np


def read_metadata(stations, metadir='data', station=None, verbose=0):
    metadata = {}
    for s in stations:
        if station and s != station:
            continue
        fname = metadir + '/' + s + '/metadata.json'
        if not os.path.exists(fname):
            metadata[s] = {}
            continue
        if verbose > 1:
            print('reading', fname)
        with open(fname) as fd:
            metadata[s] = json.load(fd)
    return metadata


def write_metadata(metadata, metadir='data', station=None, verbose=0):
    for s, meta in metadata.items():
        if station and s != station:
            continue
        dirname = metadir + '/' + s
        os.makedirs(dirname, exist_ok=True)
        fname = dirname + '/metadata.json'
        if verbose > 1:
            print('writing', fname)
        with open(fname, 'w') as fd:
            json.dump(meta, fd, sort_keys=True, indent=4)


def read_masterlist(fname='masterlist.json'):
    with open(fname) as f:
        masterlist = json.load(f)

    stations = []
    for thing in masterlist:
        if thing != 'default':
            stations.append(thing)
        # extract stations (everything but "default")
        # extras:
        # JCMT recorder_2, telescope_observingMode
        # LMT maser
        # PICO rx
        # SMA maser, telescope_extract

    parameters = {}
    for p, v in masterlist['default'].items():
        if not p.isidentifier():
            raise ValueError('parameter {} is not an identifier'.format(p))

        # partype static has no cadence
        # partype derived has no cadence
        # partype optional is sometimes a constant and has a private 0 cadence, other times a normal-looking cadence
        # partype mandatory should always have a cadence ?
        # partype: "mandatory but not real time" geez
        # preserve the cadence, type, data

        #  clean "Deprecated" metrics (3 of them, in "description"
        #  partype: "derived"... none have cadence
        #  partype: "static" no cadence
        #  observatory_timeZone is partype "optional" cadence private 0
        #  many other optionals update frequently, like telescope_azimuthElevation

        #if 'cadence' in v and 'public' in v['cadence']:
        #    parameters[p] = v
        parameters[p] = v

    return stations, parameters


def debug_cadence(points, station=None, param=None, verbose=0):
    if len(points) < 2:
        return None
    arr = np.array([p[0] for p in points])
    diff = np.diff(arr)
    problem = [t for t in diff if t < 0]
    if problem:
        print('debug_cadence for {} {}'.format(station, param))
        print(' saw a problem in observed cadence, which should be monotonically increasing:', points)


def comment_on_masterlist(stations, parameters, verbose=0):
    if not verbose:
        return
    print('stations', stations)
    print('len params', len(parameters))
    print(' ', 'len params public', len([x for x in parameters.items() if 'cadence' in x[1] and 'public' in x[1]['cadence']]))
    print(' ', 'len params private', len([x for x in parameters.items() if 'cadence' in x[1] and 'private' in x[1]['cadence']]))


def flatten(snap, add_points=False, to_int=True, verbose=0):
    ret = []
    for s, v in snap.items():
        if s == 'vexfiles':
            continue
        if 'clients' in v:
            for c, v2 in v['clients'].items():
                # these client things need a param that is a valid identifier
                # except they're boring -- just a version number -- no version for 127.0.0.1
                # so skip them all
                #c = c.replace(' ', '_').replace('.', '_')
                #line = [s, c, v2['recvTime'], v2.get('version', 'no_version')]
                #ret.append(line)
                pass
        if 'data' in v:
            for d, v2 in v['data'].items():
                recvTime = v2[0]
                if to_int:
                    recvTime = int(recvTime)
                value = v2[1]
                line = [s, d, recvTime, value]
                ret.append(line)
    if add_points:
        points = len(ret)
        latest_point = int(time.time()) if len(ret) == 0 else max([r[2] for r in ret])
        lag = time.time() - latest_point  # float
        now = int(time.time())
        station_points = defaultdict(int)
        for r in ret:
            station_points[r[0]] += 1
        for s, value in station_points.items():
            if value > 0:
                ret.append([s, 'points', int(time.time()), value])
        ret.append(['bridge', 'points', now, points])  # do this last so these are not counted for station 'bridge'
        ret.append(['bridge', 'lag', now, lag])

    if verbose > 1:
        [print(r) for r in ret]
    return ret


def flat_to_tables(flat):
    # flat record: station, param, time, value
    # sql tables are named param and the rows are time, station, value
    tables = defaultdict(list)
    for f in flat:
        station, param, recv_time, value = f
        tables[param].append((recv_time, station, value),)
    return tables


def setup_groups(verbose=0):
    if os.name not in ('posix',):
        print('this module is not tested on the current os', os.name, file=sys.stderr)
    if sys.platform in ('wasi', 'emscripten'):
        # these identify as 'posix' but do not support all of the os module
        print('this module is not tested on the current platform', sys.platform, file=sys.stderr)

    try:
        old = os.umask(0o002)
    except OSError:
        print('error trying to set the umask to 002', file=sys.stderr)
        raise
    if old != 0o002:
        print('umask was not already 002, changed it', file=sys.stderr)

    grafana = grp.getgrnam('grafana')
    username = os.getlogin()
    if username not in grafana.gr_mem:
        print('warning: this user is not a member of the grafana group.', file=sys.stderr)


def checkout_db(fname, mode='w'):
    if mode == 'r':
        if not os.path.exists(fname):
            print('fnamedoes not exist:', fname, file=sys.stderr)
        if not os.path.isfile(fname):
            print('fname is not a file:', fname, file=sys.stderr)
        if not os.access(fname, os.R_OK, follow_symlinks=True):
            # to do: handle NotImplementedError
            print('fname cannot be read:', fname, file=sys.stderr)
    elif mode == 'w':
        if os.path.exists(fname):
            if not os.path.isfile(fname):
                print('must be a file:', fname, file=sys.stderr)
            if not os.access(fname, os.R_OK | os.W_OK, follow_symlinks=True):
                print('must to be able to read and write file:', fname, file=sys.stderr)
        head, tail = os.path.split(fname)
        if not os.access(head, os.W_OK, follow_symlinks=True):
            print('I must be about to write the directory in order for WAL to work:', head, file=sys.stderr)
    else:
        print('unknown mode', mode)
