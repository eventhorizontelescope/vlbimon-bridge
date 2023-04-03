from argparse import ArgumentParser
import time
import os
import os.path
import json

from . import history
from . import client
from . import utils
from . import transformer
from . import sqlite


def main(args=None):
    parser = ArgumentParser(description='vlbimon_bridge command line utilities')

    parser.add_argument('--verbose', '-v', action='count', help='be verbose')
    parser.add_argument('-1', dest='one', action='store_true', help='use vlbimon1 (default is vlbimon2)')
    parser.add_argument('--start', action='store', type=int, help='start time (unixtime integer)')
    parser.add_argument('--datadir', action='store', default='data', help='directory to write output in')

    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True

    hist = subparsers.add_parser('history', help='')
    hist.add_argument('--public', action='store_true', help='process public parameters (year round)')
    hist.add_argument('--private', action='store_true', help='process private parameters (during EHT obs)')
    hist.add_argument('--all', action='store_true', help='process all parameters')
    hist.add_argument('--end', action='store', type=int, help='end time (unixtime integer)')
    hist.add_argument('--param', action='append', help='param to process (default all)')
    hist.add_argument('--stations', action='append', help='stations to process (default all)')
    hist.set_defaults(func=history.history)

    initdb = subparsers.add_parser('initdb', help='initialize a sqlite database')
    initdb.add_argument('--wal', action='store', type=int, default=10000, help='size of the write ahead log, default 10000 4k pages')
    initdb.add_argument('--sqlitedb', action='store', default='vlbimon.db', help='name of the output database; elsewise, print to stdout')
    initdb.set_defaults(func=sqlite.initdb)

    snap = subparsers.add_parser('snapshot', help='bridge data from vlbimon into a sqlite database')
    snap.add_argument('--dt', action='store', type=int, default=10, help='time between calls, seconds, default=10')
    snap.add_argument('--sqlitedb', action='store', help='name of the output database; elsewise, print to stdout')
    snap.set_defaults(func=snapshot_cli)

    cmd = parser.parse_args(args=args)
    cmd.func(cmd)


def snapshot_cli(cmd):
    verbose = cmd.verbose
    datadir = cmd.datadir.rstrip('/')

    transformer.init(verbose=verbose)
    if cmd.one:
        server = 'vlbimon1.science.ru.nl'
    else:
        server = 'vlbimon2.science.ru.nl'
    auth = client.get_auth(server)

    os.makedirs(datadir, exist_ok=True)
    metadata_file = datadir + '/' + server + '.json'
    sessionid = None
    if os.path.isfile(metadata_file):
        with open(metadata_file) as f:
            try:
                j = json.load(f)
                sessionid = j['sessionid']
                last_snap = j['last_snap']
            except json.JSONDecodeError as e:
                print('surprised while reading {} by {}, ignoring metadata'.format(metadata_file, repr(e)))
    if sessionid is None:
        sessionid = client.get_sessionid(server, auth=auth)
        last_snap = int(time.time())
    if cmd.start:  # overrides
        last_snap = cmd.start

    next_deadline = 0
    server = 'https://' + server

    while True:
        if next_deadline:
            time.sleep(next_deadline - time.time())
        next_deadline = time.time() + cmd.dt

        sessionid, last_snap, snap = client.get_snapshot(server, last_snap=last_snap, sessionid=sessionid, auth=auth)
        flat = utils.flatten(snap, add_points=True, verbose=verbose)
        flat = transformer.transform(flat, verbose=verbose)

        with open(metadata_file, 'w') as f:
            json.dump({'sessionid': sessionid, 'last_snap': last_snap}, f, sort_keys=True)

        print('I got:')
        [print(f) for f in flat]
