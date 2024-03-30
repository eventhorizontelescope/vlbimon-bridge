'''
This script does the addition of tables to make Remo's status page
'''

import sys
import os.path
import sqlite3

import vlbimon_bridge.utils


if len(sys.argv) == 3:
    verb = sys.argv[1]
    db = sys.argv[2]
elif len(sys.argv) == 1:
    verb = 'check'
    db = 'vlbimon.db'
else:
    print('usage: python create_remo.py {check,fix} dbname')
    exit(1)

# checks file and directory permissions
vlbimon_bridge.utils.checkout_db(db, mode='r')

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

renames = {
    'lag': 'totalLag',
}

new_tables = [
    'bridgeLag',  # ts_param_bridgeLag
    'forecast_tau225',
    'windSpeed',
    'windGust',
]


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


if verb == 'check':
    exit(0)
if old_count != len(renames) or new_count > 0:
    print('not changing anything')
    exit(1)

# checks file and directory permissions -- for writing
print('fixing')
vlbimon_bridge.utils.checkout_db(db, mode='w')

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

for new in new_tables:
    new = 'ts_param_'+new
    cur.execute('CREATE TABLE {} (time INTEGER NOT NULL, station TEXT NOT NULL, value {})'.format(new, 'REAL'))
    cur.execute('CREATE INDEX idx_{}_time ON {}(time)'.format(new, new))
    cur.execute('CREATE INDEX idx_{}_station ON {}(station)'.format(new, new))

# schedule has an unusual schema
cur.execute('CREATE TABLE ts_param_schedule (time INTEGER NOT NULL, stations TEXT NOT NULL, scanname TEXT NOT NULL)')
cur.execute('CREATE INDEX idx_ts_param_schedule_time ON ts_param_schedule(time)')

cur.execute('ALTER TABLE station_status ADD tsys REAL')
cur.execute('ALTER TABLE station_status ADD tau225 REAL')
cur.execute('ALTER TABLE station_status ADD scan TEXT NOT NULL DEFAULT ""')

cur.close()
con.commit()
con.close()
print('done')
