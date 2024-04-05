import sqlite3


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


def check_old_new(names, renames, new_tables):
    # we don't check column renames

    old_count = sum(['ts_param_'+n in names for n in renames.keys()])
    if old_count == len(renames):
        print('all old tables are present')
    elif old_count == 0:
        print('no old tables are present')
    else:
        print('some old tables are missing?')
        for n in renames.keys():
            if n not in names:
                print(' ', n)
        raise ValueError('not all old tables are present')

    newts = [str(r) for r in renames.values()]
    newts.extend(new_tables)
    newts.append('schedule')
    new_count = sum(['ts_param_'+n in names for n in newts])
    if new_count == len(newts):
        print('all new tables are present')
    elif new_count == 0:
        print('no new tables are present')
    else:
        print('some new tables are missing?')
        for n in newts:
            if 'ts_param_'+n not in names:
                print(' ', n)
        raise ValueError('not all new tables are present')

    return old_count, new_count


def do_table_renames(db, renames):
    con = sqlite3.connect(db)
    cur = con.cursor()
    for old, new in renames.items():
        old = 'ts_param_'+old
        new = 'ts_param_'+new

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


def do_new_tables(db, new_tables):
    con = sqlite3.connect(db)
    cur = con.cursor()
    for new in new_tables:
        new = 'ts_param_'+new
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
