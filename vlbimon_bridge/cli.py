from argparse import ArgumentParser
import time
import os
import os.path
import json
import sys

from . import history
from . import client
from . import utils
from . import transformer
from . import sqlite


def main(args=None):
    parser = ArgumentParser(description='vlbimon_bridge command line utilities')

    parser.add_argument('--verbose', '-v', action='count', default=0, help='be verbose')
    parser.add_argument('-1', dest='one', action='store_true', help='use vlbimon1 (default is vlbimon2)')
    parser.add_argument('--start', action='store', type=int, help='start time (unixtime integer)')
    parser.add_argument('--stations', action='append', help='stations to process (default all)')
    parser.add_argument('--datadir', action='store', default='data', help='directory to write output in')
    parser.add_argument('--secrets', action='store', default='~/.vlbimonitor-secrets.yaml', help='file containing auth secrets, default ~/.vlbimonitor-secrets.yaml')

    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True

    hist = subparsers.add_parser('history', help='')
    hist.add_argument('--public', action='store_true', help='process public parameters (year round)')
    hist.add_argument('--private', action='store_true', help='process private parameters (during EHT obs)')
    hist.add_argument('--all', action='store_true', help='process all parameters')
    hist.add_argument('--end', action='store', type=int, help='end time (unixtime integer)')
    hist.add_argument('--param', action='append', help='param to process (default all)')
    hist.set_defaults(func=history.history)

    initdb = subparsers.add_parser('initdb', help='initialize a sqlite database')
    initdb.add_argument('--wal', action='store', help='size of the write ahead log, default 1000 4k pages. 0 to disable.')
    initdb.add_argument('--sqlitedb', action='store', default='vlbimon.db', help='name of the output database; elsewise, print to stdout')
    initdb.set_defaults(func=sqlite.initdb)

    bridge = subparsers.add_parser('bridge', help='bridge data from vlbimon into a sqlite database')
    bridge.add_argument('--dt', action='store', type=int, default=10, help='time between calls, seconds, default=10')
    bridge.add_argument('--sqlitedb', action='store', default='vlbimon.db', help='name of the output database; elsewise, print to stdout')
    bridge.set_defaults(func=bridge_cli)

    cmd = parser.parse_args(args=args)
    return cmd.func(cmd)


def bridge_cli(cmd):
    verbose = cmd.verbose
    datadir = cmd.datadir.rstrip('/')
    secrets = cmd.secrets
    exit_file = datadir + '/PLEASE-EXIT'

    if not os.path.isfile(cmd.sqlitedb):
        # error out early if the db doesn't exist
        raise ValueError('database file {} does not exist'.format(cmd.sqlitedb))

    stations = transformer.init(verbose=verbose)
    stations = cmd.stations or stations

    if cmd.one:
        server = 'vlbimon1.science.ru.nl'
    else:
        server = 'vlbimon2.science.ru.nl'
    auth = client.get_auth(server, secrets=secrets)

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
                print('surprised while reading {} by {}, ignoring metadata'.format(metadata_file, repr(e)), file=sys.stderr)
    if sessionid is None:
        sessionid = client.get_sessionid(server, auth=auth)
        last_snap = int(time.time())
    if cmd.start:  # overrides
        last_snap = cmd.start

    next_deadline = 0
    server = 'https://' + server
    con = sqlite.connect(cmd.sqlitedb, verbose=verbose)
    station_status = transformer.init_station_status(con, stations, verbose=verbose)

    try:
        while True:
            if next_deadline:
                gap = next_deadline - time.time()
                if gap > 0:
                    time.sleep(gap)
            next_deadline = time.time() + cmd.dt

            sessionid, last_snap, snap = client.get_snapshot(server, last_snap=last_snap, sessionid=sessionid, auth=auth)
            flat = utils.flatten(snap, add_points=True, verbose=verbose)
            flat = transformer.transform(flat, verbose=verbose, dedup_events=True)
            tables = utils.flat_to_tables(flat)
            status_table = transformer.update_station_status(station_status, tables, verbose=verbose)

            sqlite.insert_many_ts(con, tables, verbose=verbose)
            sqlite.insert_many_status(con, status_table, verbose=verbose)
            con.commit()

            with open(metadata_file, 'w') as f:
                # do this after successful database writes
                # XXX maybe new + os.replace()
                json.dump({'sessionid': sessionid, 'last_snap': last_snap}, f, sort_keys=True)

            if os.path.exists(exit_file):
                print('exiting on', exit_file, file=sys.stderr)
                try:
                    os.remove(exit_file)
                except FileNotFoundError:
                    pass
                break
    except KeyboardInterrupt:
        print('^C seen, gracefully closing database', file=sys.stderr)
        sys.stderr.flush()
        con.close()
        raise
