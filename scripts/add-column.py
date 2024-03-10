import sqlite3


stations = ['ALMA', 'APEX', 'GLT', 'JCMT', 'KP', 'LMT', 'NOEMA', 'PICO', 'SMA', 'SMTO', 'SPT']
client_tables = [
    '{}_central',
    '{}_concom',
    '127_0_0_1',  # just one of these
]


con = sqlite3.connect('vlbimon.db')
cur = con.cursor()
param = 'points'
vlbi_type = 'INTEGER'
cur.execute('CREATE TABLE ts_param_{} (time INTEGER NOT NULL, station TEXT NOT NULL, value {})'.format(param, vlbi_type))
cur.execute('CREATE INDEX idx_ts_param_{}_time ON ts_param_{}(time)'.format(param, param))
cur.execute('CREATE INDEX idx_ts_param_{}_station ON ts_param_{}(station)'.format(param, param))
con.commit()
con.close()

'''
Change type example: destroy old table and create the new one

DROP INDEX IF EXISTS idx_ts_param_lag_time;
DROP INDEX IF EXISTS idx_ts_param_lag_station;
DROP TABLE IF EXISTS ts_param_lag;

CREATE TABLE ts_param_lag (time INTEGER NOT NULL, station TEXT NOT NULL, VALUE REAL);
CREATE INDEX idx_ts_param_lag_time ON ts_param_lag(time);
CREATE INDEX idx_ts_param_lag_station ON ts_param_lag(station);
'''
