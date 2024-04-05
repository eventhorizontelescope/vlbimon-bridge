import sqlite3


def parse_argv(argv):
    if len(argv) == 3:
        verb = argv[1]
        db = argv[2]
    elif len(argv) == 1:
        verb = 'check'
        db = 'vlbimon.db'
    else:
        print('usage:', argv[0], '{check,fix} dbname')
        exit(1)
    return verb, db


def get_tables(db):
    con = sqlite3.connect(db)
    cur = con.cursor()
    res = cur.execute('SELECT name FROM sqlite_master')
    names = res.fetchall()  # iterable of tuples of length 1
    names = set(n[0] for n in names)

    # if I close the con now it will resolve the WAL? or only if I actually wrote something
    cur.close()
    con.commit()  # should be empty
    con.close()

    if False:
        # we haven't written yet
        # if there's still a WAL, error out
        if os.path.exists(db + '-wal'):
            raise ValueError(db+'-wal still exists, aborting')
        if os.path.exists(db + '-shm'):
            raise ValueError(db+'-shm still exists, aborting')

    return names


def check_old_new(names, table_renames, new_tables, prefix='ts_param_'):
    # we don't check column renames, just table renames and new tables

    old_count = sum([prefix+n in names for n in table_renames.keys()])
    if old_count == len(table_renames):
        print('all old tables are present')
    elif old_count == 0:
        print('no old tables are present')
    else:
        print('some old tables are missing?')
        for n in table_renames.keys():
            if n not in names:
                print(' ', n)
        raise ValueError('not all old tables are present')

    newts = [str(r) for r in table_renames.values()]
    newts.extend(new_tables)
    new_count = sum([prefix+n in names for n in newts])
    if new_count == len(newts):
        print('all new tables are present')
    elif new_count == 0:
        print('no new tables are present')
    else:
        print('some new tables are present?')
        for n in newts:
            if prefix+n in names:
                print(' ', n)
        raise ValueError('some new tables are present')

    return old_count, new_count


def do_table_renames(db, renames, prefix='ts_param_'):
    con = sqlite3.connect(db)
    cur = con.cursor()
    for old, new in renames.items():
        old = prefix+old
        new = prefix+new

        cur.execute('ALTER TABLE {} RENAME TO {}'.format(old, new))

        # drop the old index
        cur.execute('DROP INDEX idx_{}_time'.format(old))
        cur.execute('DROP INDEX idx_{}_station'.format(old))

        # add a new index
        cur.execute('CREATE INDEX idx_{}_time ON {}(time)'.format(new, new))
        cur.execute('CREATE INDEX idx_{}_station ON {}(station)'.format(new, new))
    cur.close()
    con.commit()
    con.close()


def do_new_tables(db, new_tables, prefix='ts_param_'):
    con = sqlite3.connect(db)
    cur = con.cursor()
    for new in new_tables:
        new = prefix+new
        cur.execute('CREATE TABLE {} (time INTEGER NOT NULL, station TEXT NOT NULL, value {})'.format(new, 'REAL'))
        cur.execute('CREATE INDEX idx_{}_time ON {}(time)'.format(new, new))
        cur.execute('CREATE INDEX idx_{}_station ON {}(station)'.format(new, new))
    cur.close()
    con.commit()
    con.close()


def do_stuff(db, stuff):
    con = sqlite3.connect(db)
    cur = con.cursor()
    for s in stuff:
        cur.execute(s)
    cur.close()
    con.commit()
    con.close()
