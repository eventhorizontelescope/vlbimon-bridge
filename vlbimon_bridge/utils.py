import os.path
import json

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
