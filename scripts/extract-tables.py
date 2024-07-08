import sys
from collections import defaultdict
import datetime
import csv

import sqlite3

TIMESTAMP = '%Y%m%d%H%M%S'


db = sys.argv[1]
pattern = sys.argv[2]

con = sqlite3.connect(db)
cur = con.cursor()

res = cur.execute('SELECT name FROM sqlite_master')
names = res.fetchall()

for name in names:
    name = name[0]  # tuple of length 1
    if name.startswith('idx_'):
        continue
    if pattern not in name:
        continue
    if not name.startswith('ts_param_'):
        continue

    query = 'SELECT time, station, value from {} ORDER BY time'
    res = cur.execute(query.format(name))
    rows = res.fetchall()

    if not res:
        print('not res')
        continue

    if not rows:
        continue

    new = []
    for row in rows:
        # this is a list
        t = int(row[0])
        ts = datetime.datetime.fromtimestamp(t, tz=datetime.timezone.utc).strftime(TIMESTAMP)
        new.append((t, ts, *row[1:]))
    rows = new

    fname = name.replace('ts_param_', '', 1)

    with open(fname + '.csv', 'w', newline='') as fd:
        csv_writer = csv.writer(fd)
        csv_writer.writerow([x[0] for x in res.description])
        csv_writer.writerows(rows)
