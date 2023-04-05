import os.path
import sys

import sqlite3

from . import types
from . import transformer


vlbi_types = types.get_types()
to_sql_types = {
    int: 'INTEGER',
    float: 'REAL',
    str: 'TEXT',
    bool: 'BOOLEAN',
}
vlbi_types = dict([(name, to_sql_types[ty]) for name, ty in vlbi_types.items()])

stations = ['ALMA', 'APEX', 'GLT', 'JCMT', 'KP', 'LMT', 'NOEMA', 'PICO', 'SMA', 'SMTO', 'SPT']

client_tables = [
    '{}_central',
    '{}_concom',
    '127_0_0_1',  # just one of these
]


def initdb(cmd):
    verbose = cmd.verbose
    sqlitedb = cmd.sqlitedb

    if os.path.exists(sqlitedb):
        raise ValueError('file found: {} refusing to overwrite'.format(sqlitedb))

    if verbose:
        print('initializing sqlite db', sqlitedb, file=sys.stderr)
    con = sqlite3.connect(sqlitedb)
    cur = con.cursor()

    transformer.init(verbose=verbose)
    for param in transformer.splitters_expanded:
        if param not in vlbi_types:
            vlbi_types[param] = 'REAL'

    for param, vlbi_type in vlbi_types.items():
        param = param.split('.')[0]
        print(param, vlbi_type)
        add_timeseries(cur, param, vlbi_type, verbose=verbose)

    bridge_tables = (
        ('events', 'TEXT'),
        ('points', 'INTEGER'),
        ('lag', 'REAL'),
    )
    for param, vlbi_type in bridge_tables:
        add_timeseries(cur, param, vlbi_type, verbose=verbose)

    if cmd.wal:
        configure_wal(cur, cmd.wal, verbose=verbose)


def add_timeseries(cur, param, vlbi_type, verbose=0):
    cur.execute('CREATE TABLE ts_param_{} (time INTEGER NOT NULL, station TEXT NOT NULL, value {})'.format(param, vlbi_type))
    cur.execute('CREATE INDEX idx_ts_param_{}_time ON ts_param_{}(time)'.format(param, param))
    cur.execute('CREATE INDEX idx_ts_param_{}_station ON ts_param_{}(station)'.format(param, param))


def configure_wal(cur, wal_size, verbose=0):
    if verbose:
        print('setting up Write Ahead Log (WAL) in squlite db, size in pages is', wal_size, file=sys.stderr)
    cur.execute('PRAGMA journal_mode=WAL')
    cur.execute('PRAGMA synchronous=NORMAL')  # recommended for WAL. affects "main" database
    cur.execute('PRAGMA wal_autocheckpoint={}'.format(wal_size))  # defaults to 1000 4k pages (4 MB)
