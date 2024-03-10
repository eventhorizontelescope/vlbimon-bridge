import os.path
import sys
import time

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

    cur.execute('CREATE TABLE station_status (time INTEGER NOT NULL, station TEXT NOT NULL PRIMARY KEY, source TEXT NOT NULL, onsource TEXT NOT NULL, mode TEXT NOT NULL, recording TEXT NOT NULL)')
    # sqlite will create sqlite_autoindex_station_status_1 because of the primary key

    if cmd.wal != 0:
        # cli.py default is None, which != 0
        configure_wal(cur, cmd.wal, verbose=verbose)

    cur.close()
    con.commit()
    con.close()


def connect(database, *args, verbose=0, **kwargs):
    con = sqlite3.connect(database, *args, **kwargs)

    cur = con.cursor()
    configure_wal(cur, verbose=verbose)
    cur.execute('PRAGMA busy_timeout=100')
    cur.close()

    if verbose:
        cur = con.cursor()
        for row in cur.execute('PRAGMA journal_mode'):
            assert row[0] == 'wal'
        for row in cur.execute('PRAGMA synchronous'):
            print(row)
            assert row[0] == 1  # 1=NORMAL, does not persist
        for row in cur.execute('PRAGMA wal_autocheckpoint'):
            assert row[0] == 1000  # the default
        for row in cur.execute('PRAGMA busy_timeout'):
            assert row[0] == 100
        cur.close()
    return con


def add_timeseries(cur, param, vlbi_type, verbose=0):
    cur.execute('CREATE TABLE ts_param_{} (time INTEGER NOT NULL, station TEXT NOT NULL, value {})'.format(param, vlbi_type))
    cur.execute('CREATE INDEX idx_ts_param_{}_time ON ts_param_{}(time)'.format(param, param))
    cur.execute('CREATE INDEX idx_ts_param_{}_station ON ts_param_{}(station)'.format(param, param))


def configure_wal(cur, wal_size=None, verbose=0):
    if verbose:
        print('setting up Write Ahead Log (WAL) in sqlite db, size in pages is', wal_size, file=sys.stderr)
    cur.execute('PRAGMA journal_mode=WAL')
    # recommended for WAL. affects "main" database, does not persist
    cur.execute('PRAGMA synchronous=NORMAL')
    if wal_size is not None:
        # defaults to 1000 4k pages (4 MB), does not persist
        cur.execute('PRAGMA wal_autocheckpoint={}'.format(wal_size))


def insert_many_ts(con, tables, verbose=0):
    t = time.time()
    cur = con.cursor()

    if verbose:
        print('inserting', len(tables), 'items', file=sys.stderr)

    for param, data in tables.items():
        try:
            cur.executemany('INSERT INTO ts_param_{} VALUES(?, ?, ?)'.format(param), data)
        except sqlite3.OperationalError as e:
            # sqlite3.OperationalError: no such table: ts_param_127_0_0_1
            if verbose:
                print('skipping', repr(e), data, file=sys.stderr)
            pass

    cur.close()

    if verbose > 1:
        print('sqlite insert_many took {} seconds'.format(round(time.time() - t, 3)))


def insert_many_status(con, status_table, verbose=0):
    if status_table:
        cur = con.cursor()

        if verbose:
            print('inserting', len(status_table), 'station_status updates', file=sys.stderr)

        cur.executemany('INSERT OR REPLACE INTO station_status VALUES(?, ?, ?, ?, ?, ?)', status_table)

        cur.close()


def get_station_status(con, verbose=0):
    cur = con.cursor()
    cur.row_factory = sqlite3.Row
    cur.execute('SELECT * FROM station_status')
    rows = cur.fetchall()
    cur.close()
    return rows
