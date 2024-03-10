import json


type_map = {
    'AzElCoordinates': 'str',
    'CelestialCoordinates': 'str',
    'Coordinates': 'str',
    'boolean': 'bool',
    'document': 'str',
    'float': 'float',
    'int': 'int',
    'none': '',
    'number': 'float',
    'string': 'str',
}

'''
Traceback (most recent call last):
  File "/home/astrogreg/github/eht-monitor-demo/insert_station.py", line 40, in <module>
    raise ValueError('invalid line: '+line)
ValueError: invalid line: 1647537129,1,2
'''

fixups = {
    'recorder_1_groupaSpaceLeft.csv': 'float',
    'recorder_1_groupbSpaceLeft.csv': 'float',
    'recorder_1_groupcSpaceLeft.csv': 'float',
    'recorder_1_groupdSpaceLeft.csv': 'float',
    'recorder_2_groupaSpaceLeft.csv': 'float',
    'recorder_2_groupbSpaceLeft.csv': 'float',
    'recorder_2_groupcSpaceLeft.csv': 'float',
    'recorder_2_groupdSpaceLeft.csv': 'float',
    'recorder_3_groupaSpaceLeft.csv': 'float',
    'recorder_3_groupbSpaceLeft.csv': 'float',
    'recorder_3_groupcSpaceLeft.csv': 'float',
    'recorder_3_groupdSpaceLeft.csv': 'float',
    'recorder_4_groupaSpaceLeft.csv': 'float',
    'recorder_4_groupbSpaceLeft.csv': 'float',
    'recorder_4_groupcSpaceLeft.csv': 'float',
    'recorder_4_groupdSpaceLeft.csv': 'float',
    'recorder_1_groupaTimeLeft.csv': 'float',
    'recorder_1_groupbTimeLeft.csv': 'float',
    'recorder_1_groupcTimeLeft.csv': 'float',
    'recorder_1_groupdTimeLeft.csv': 'float',
    'recorder_2_groupaTimeLeft.csv': 'float',
    'recorder_2_groupbTimeLeft.csv': 'float',
    'recorder_2_groupcTimeLeft.csv': 'float',
    'recorder_2_groupdTimeLeft.csv': 'float',
    'recorder_3_groupaTimeLeft.csv': 'float',
    'recorder_3_groupbTimeLeft.csv': 'float',
    'recorder_3_groupcTimeLeft.csv': 'float',
    'recorder_3_groupdTimeLeft.csv': 'float',
    'recorder_4_groupaTimeLeft.csv': 'float',
    'recorder_4_groupbTimeLeft.csv': 'float',
    'recorder_4_groupcTimeLeft.csv': 'float',
    'recorder_4_groupdTimeLeft.csv': 'float',
    'recorder_1_groupaDatarate.csv': 'float',
    'recorder_1_groupbDatarate.csv': 'float',
    'recorder_1_groupcDatarate.csv': 'float',
    'recorder_1_groupdDatarate.csv': 'float',
    'recorder_2_groupaDatarate.csv': 'float',
    'recorder_2_groupbDatarate.csv': 'float',
    'recorder_2_groupcDatarate.csv': 'float',
    'recorder_2_groupdDatarate.csv': 'float',
    'recorder_3_groupaDatarate.csv': 'float',
    'recorder_3_groupbDatarate.csv': 'float',
    'recorder_3_groupcDatarate.csv': 'float',
    'recorder_3_groupdDatarate.csv': 'float',
    'recorder_4_groupaDatarate.csv': 'float',
    'recorder_4_groupbDatarate.csv': 'float',
    'recorder_4_groupcDatarate.csv': 'float',
    'recorder_4_groupdDatarate.csv': 'float',
}

with open('masterlist.json') as fp:
    j = json.load(fp)

j = j['default']

for k, v in j.items():
    dt = type_map[v['datatype']]
    k = k + '.csv'
    if k in fixups:
        dt = fixups[k]

    if dt:
        print(','.join((k, dt)))
