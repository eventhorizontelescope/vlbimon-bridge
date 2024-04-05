'''
This script does the addition of tables to make Remo's status page
'''

import sys
import os.path
import sqlite3

import vlbimon_bridge.utils
import vlbimon_bridge.migrate as migrate


if len(sys.argv) == 3:
    verb = sys.argv[1]
    db = sys.argv[2]
elif len(sys.argv) == 1:
    verb = 'check'
    db = 'vlbimon.db'
else:
    print('usage:', sys.argv[0], '{check,fix} dbname')
    exit(1)

# checks file and directory permissions
vlbimon_bridge.utils.checkout_db(db, mode='r')

names = migrate.get_tables(db)

renames = {
    'lag': 'totalLag',
}

new_tables = [
    'bridgeLag',  # ts_param_bridgeLag
    'forecast_tau225',  # this prefix is new
    'windSpeed',  # confusing because of weather_windSpeed already existing
    'windGust',  # not confusing because there is no weather_windGust
]

old_count, new_count = migrate.check_old_new(names, renames, new_tables)

if verb == 'check':
    exit(0)
if old_count != len(renames) or new_count > 0:
    print('not changing anything')
    exit(1)

# checks file and directory permissions -- for writing
print('fixing')
vlbimon_bridge.utils.checkout_db(db, mode='w')

migrate.do_table_renames(db, renames)
migrate.do_new_timeseries(db, new_tables)

# these things are not part of the check
stuff = [
    # schedule has an unusual schema
    ('CREATE TABLE ts_param_schedule (time INTEGER NOT NULL, stations TEXT NOT NULL, scanname TEXT NOT NULL)'),
    ('CREATE INDEX idx_ts_param_schedule_time ON ts_param_schedule(time)'),
    # column additions
    ('ALTER TABLE station_status ADD tsys REAL'),
    ('ALTER TABLE station_status ADD tau225 REAL'),
    ('ALTER TABLE station_status ADD scan TEXT NOT NULL DEFAULT ""'),
    # column renames
    # 'ALTER TABLE foo RENAME COLUMN bar TO baz'
]
migrate.do_stuff(db, stuff)

print('done')
