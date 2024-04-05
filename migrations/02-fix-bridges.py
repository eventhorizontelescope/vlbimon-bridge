import sys

import vlbimon_bridge.utils
import vlbimon_bridge.migrate as migrate


table_renames = {
    'points': 'bridge_points',
    'bridgeLag': 'bridge_bridgeLag',
    'totalLag': 'bridge_totalLag',
    'events': 'bridge_events',
    'forecast_tau225': 'bridge_forecastTau225',
    'windSpeed': 'bridge_avgWindSpeed',
}
new_tables = []
another_rename = {'station_status': 'bridge_stationStatus'}  # no prefix

verb, db = migrate.parse_argv(sys.argv)
vlbimon_bridge.utils.checkout_db(db, mode='r')
names = migrate.get_tables(db)
old_count, new_count = migrate.check_old_new(names, table_renames, new_tables)

if verb == 'check':
    exit(0)
if old_count != len(table_renames) or new_count > 0:
    print('not changing anything')
    exit(1)

print('fixing')
vlbimon_bridge.utils.checkout_db(db, mode='w')

migrate.do_table_renames(db, table_renames)
migrate.do_new_timeseries(db, new_tables)
migrate.do_table_renames(db, another_rename, prefix='')

print('done')
