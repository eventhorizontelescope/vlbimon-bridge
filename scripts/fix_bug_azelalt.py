'''
This script fixes a bug with the naming of some transformed parameters
in the vlbimon bridge. A bunch of azmuth/elevation params were split
into the names ra/dec instead, and also one parameter was split into
the names alt/az instead az/el (the radio telescope standard.)

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
    print('usage: pythong fix_bug_azelalt.py {check,fix} dbname')
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
    'telescope_azimuthElevation_alt': 'telescope_azimuthElevation_el',
    'if_1_systemTempAzel_dec': 'if_1_systemTempAzel_el',
    'if_1_systemTempAzel_ra': 'if_1_systemTempAzel_az',
    'if_2_systemTempAzel_dec': 'if_2_systemTempAzel_el',
    'if_2_systemTempAzel_ra': 'if_2_systemTempAzel_az',
    'if_3_systemTempAzel_dec': 'if_3_systemTempAzel_el',
    'if_3_systemTempAzel_ra': 'if_3_systemTempAzel_az',
    'if_4_systemTempAzel_dec': 'if_4_systemTempAzel_el',
    'if_4_systemTempAzel_ra': 'if_4_systemTempAzel_az',
}

count = sum(['ts_param_'+n in names for n in renames.keys()])
if count == len(renames):
    print('all renamed tables are present')
elif count == 0:
    print('no renamed tables are present')
else:
    print('some tables are missing?')
    for n in renames.keys():
        if n not in names:
            print(' ', n)
    raise ValueError('not all renames are present')

if verb == 'check' or count == 0:
    exit(0)

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

cur.close()
con.commit()
con.close()
print('done')
