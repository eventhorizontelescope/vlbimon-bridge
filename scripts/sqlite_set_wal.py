import sys
import sqlite3

db_file = sys.argv[1]


con = sqlite3.connect(db_file)
cur = con.cursor()

print('starting setup of WAL (write ahead log)')
nwal = 10000
cur.execute('PRAGMA journal_mode=WAL')
cur.execute('PRAGMA synchronous=NORMAL')  # recommended for WAL. affects "main" database
cur.execute('PRAGMA wal_autocheckpoint={}'.format(nwal))  # defaults to 1000 4k pages (4 MB)
con.commit()
con.close()
print(' finished')
