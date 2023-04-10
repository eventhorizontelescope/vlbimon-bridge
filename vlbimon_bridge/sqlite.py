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
    con = connect(sqlitedb)
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


def connect(database, *args, verbose=0, **kwargs):
    con = sqlite3.connect(database, *args, **kwargs)
    if verbose:
        cur = con.cursor()
        for row in cur.execute('PRAGMA journal_mode'):  # WAL, geting WAL
            print(row)
        for row in cur.execute('PRAGMA synchronous'):  # NORMAL, getting 2
            print(row)
        for row in cur.execute('PRAGMA wal_autocheckpoint'):  # 10000, getting 1000 (?)
            print(row)
        cur.close()
    return con


def add_timeseries(cur, param, vlbi_type, verbose=0):
    cur.execute('CREATE TABLE ts_param_{} (time INTEGER NOT NULL, station TEXT NOT NULL, value {})'.format(param, vlbi_type))
    cur.execute('CREATE INDEX idx_ts_param_{}_time ON ts_param_{}(time)'.format(param, param))
    cur.execute('CREATE INDEX idx_ts_param_{}_station ON ts_param_{}(station)'.format(param, param))


def configure_wal(cur, wal_size, verbose=0):
    if verbose:
        print('setting up Write Ahead Log (WAL) in sqlite db, size in pages is', wal_size, file=sys.stderr)
    cur.execute('PRAGMA journal_mode=WAL')
    cur.execute('PRAGMA synchronous=NORMAL')  # recommended for WAL. affects "main" database
    cur.execute('PRAGMA wal_autocheckpoint={}'.format(wal_size))  # defaults to 1000 4k pages (4 MB)


def insert_many(tables, sqlitedb, verbose=0):
    t = time.time()
    con = connect(sqlitedb, verbose=verbose)
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
    con.commit()
    con.close()

    if verbose > 1:
        print('sqlite insert_many took {} seconds'.format(round(time.time() - t, 3)))
