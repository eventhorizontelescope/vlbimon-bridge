from argparse import ArgumentParser
import time
import datetime
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
    parser.add_argument('-1', dest='one', action='store_true', help='use vlbimon1 (default)')
    parser.add_argument('-2', dest='two', action='store_true', help='use vlbimon2 (default is vlbimon1)')
    parser.add_argument('--stations', action='append', help='stations to process (default all)')
    parser.add_argument('--datadir', action='store', default='data', help='directory to write output in (default ./data)')
    parser.add_argument('--secrets', action='store', default='~/.vlbimonitor-secrets.yaml', help='file containing auth secrets, default ~/.vlbimonitor-secrets.yaml')

    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True

    hist = subparsers.add_parser('history', help='download historical vlbimon data to csv files')
    hist.add_argument('--start', action='store', type=int, help='start time (unixtime integer)')
    hist.add_argument('--end', action='store', type=int, help='end time (unixtime integer)')
    hist.add_argument('--all', action='store_true', help='process all public and private parameters')
    hist.add_argument('--public', action='store_true', help='process public parameters (year round)')
    hist.add_argument('--private', action='store_true', help='process private parameters (during EHT obs)')
    hist.add_argument('--param', action='append', help='param to process (default all)')
    hist.set_defaults(func=history.history)

    initdb = subparsers.add_parser('initdb', help='initialize a sqlite database')
    initdb.add_argument('--sqlitedb', action='store', default='vlbimon.db', help='name of the output database; elsewise, print to stdout')
    initdb.set_defaults(func=sqlite.initdb)

    bridge = subparsers.add_parser('bridge', help='bridge data from vlbimon into a sqlite database')
    bridge.add_argument('--start', action='store', type=int, help='start time (unixtime integer) (0=now) (default reads data/server.json last_snap)')
    bridge.add_argument('--dt', action='store', type=int, default=10, help='time between calls, seconds, default=10')
    bridge.add_argument('--sqlitedb', action='store', default='vlbimon.db', help='name of the output database; elsewise, print to stdout')
    bridge.add_argument('--wal', action='store', type=int, default=1000, help='size of the write ahead log, default 1000 4k pages. 0 to disable.')
    bridge.set_defaults(func=bridge_cli)

    cmd = parser.parse_args(args=args)
    return cmd.func(cmd)


def bridge_cli(cmd):
    verbose = cmd.verbose
    datadir = cmd.datadir.rstrip('/')
    secrets = cmd.secrets
    wal_size = cmd.wal
    exit_file = datadir + '/PLEASE-EXIT'

    print('bridge starting', datetime.datetime.now(datetime.timezone.utc).isoformat(), file=sys.stderr, flush=True)

    if not os.path.isfile(cmd.sqlitedb):
        # error out early if the db doesn't exist
        raise ValueError('database file {} does not exist'.format(cmd.sqlitedb))
    utils.setup_groups(verbose=verbose)

    stations = transformer.init(verbose=verbose)
    stations = cmd.stations or stations

    server, auth = client.get_server(cmd.two, secrets=secrets, verbose=verbose)

    os.makedirs(datadir, exist_ok=True)
    clean_server = server.replace('https://', '', 1).rstrip('/')
    metadata_file = datadir + '/' + clean_server + '.json'
    sessionid = None
    last_snap = int(time.time())
    if os.path.isfile(metadata_file):
        with open(metadata_file) as f:
            try:
                j = json.load(f)
                sessionid = j['sessionid']
                try:
                    last_snap = int(j['last_snap'])
                except ValueError:
                    print('invalid last_snap in', metadata_file)
            except json.JSONDecodeError as e:
                print('surprised while reading {} by {}, ignoring metadata'.format(metadata_file, repr(e)), file=sys.stderr)
        if verbose:
            print('got a valid sessionid', sessionid, 'and last snap', last_snap)
    if sessionid is None:
        sessionid = client.get_sessionid(server, auth=auth, verbose=verbose)
        # last_snap already set
    if cmd.start is not None:  # overrides .json last_snap
        if cmd.start == 0:
            last_snap = int(time.time())
        else:
            last_snap = cmd.start
    delta = int(time.time() - last_snap)
    if delta < 0:
        last_snap = int(time.time())
        delta = 0
    if verbose:
        print('fetching data starting', delta, 'seconds ago')

    next_deadline = 0
    con = sqlite.connect(cmd.sqlitedb, wal_size=wal_size, verbose=verbose)
    stationStatus = transformer.init_stationStatus(con, stations, verbose=verbose)

    try:
        while True:
            if next_deadline:
                delta = next_deadline - time.time()
                if delta > 0:
                    if verbose:
                        print('sleeping', round(delta, 3), 'seconds until the next deadline')
                    time.sleep(delta)
            now = time.time()
            next_deadline = now + cmd.dt

            sessionid, last_snap, snap = client.get_snapshot(server, last_snap=last_snap, sessionid=sessionid, auth=auth, verbose=verbose)
            bridge_lag = time.time() - now
            flat = utils.flatten(snap, bridge_lag=bridge_lag, add_points=True, verbose=verbose)
            flat = transformer.transform(flat, verbose=verbose, dedup_events=True)
            tables = utils.flat_to_tables(flat)
            status_table = transformer.update_stationStatus(stationStatus, tables, verbose=verbose)

            sqlite.insert_many_ts(con, tables, verbose=verbose)
            sqlite.insert_many_status(con, status_table, verbose=verbose)
            con.commit()

            with open(metadata_file, 'w') as f:
                # do this after successful database writes
                # XXX maybe new + os.replace()
                json.dump({'sessionid': sessionid, 'last_snap': last_snap}, f, sort_keys=True)

            if os.path.exists(exit_file):
                sys.stdout.flush()
                print('exiting on', exit_file, file=sys.stderr)
                try:
                    os.remove(exit_file)
                except FileNotFoundError:
                    pass
                break
    except KeyboardInterrupt:
        sys.stdout.flush()
        print('^C seen, gracefully closing database', file=sys.stderr, flush=True)
        con.close()
        raise
