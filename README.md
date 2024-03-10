# vlbimon-bridge

This code is a bridge from the existing EHT VLBIMonitor database to a
time-series database (currently sqlite) that feeds a Grafana instance.

It can be used in two modes:

* Downloading historical data to .csv files, and then inserting it into a database
* Real-time "bridging" of data from vlbimon to a database

## Installation

```
git clone https://github.com/wumpus/vlbimon-bridge
cd vlbimon-bridge
pip install .
make init  # downloads schema from vlbimon server, needs authentication to succeed
```

## Authentication with vlbimon

Make a file `~/.vlbimonitor-secrets.yaml` with contents like:

```
vlbimon1.science.ru.nl:
  basicauth:
  - Your Name
  - Yourpw
vlbimon2.science.ru.nl:
  basicauth:
  - Your Name
  - Yourpw
```

## Usage

```
$ vlbimon_bridge -h
usage: vlbimon_bridge [-h] [--verbose] [-1] [--start START] [--datadir DATADIR] {history,bridge} ...

vlbimon_bridge command line utilities

positional arguments:
  {history,bridge}
    history
    bridge

options:
  -h, --help         show this help message and exit
  --verbose, -v      be verbose
  -1                 use vlbimon1 server (default is vlbimon2)
  --datadir DATADIR  directory to write output in (default ./data)

$ vlbimon_bridge history -h
usage: vlbimon_bridge history [-h] [--public] [--private] [--all] [--end END] [--param PARAM] [--stations STATIONS]

options:
  -h, --help           show this help message and exit
  --public             process public parameters (year round)
  --private            process private parameters (during EHT obs)
  --all                process all parameters
  --start START        start time (unixtime integer)
  --end END            end time (unixtime integer)
  --param PARAM        param to process (default all)
  --stations STATIONS  stations to process (default all)

$ vlbimon_bridge bridge -h
usage: vlbimon_bridge bridge [-h]

options:
  -h, --help           show this help message and exit
  --start START        start time (unixtime integer) (0=now) (default data/server.json)
  --dt DT              time between calls, seconds, default=10
  --sqlitedb SQLITEDB  name of the output database; elsewise, print to stdout
```

## Download a time range from vlbimon to csv

To copy the first day of the EHT 2022 observation,

```
# remember how the date command works
$ date +%s  # now
$ date -u -d @1647543720  # unixtime to date
$ date -d 'Jan 1, 2001' -u +%s  # utc date into a unixtime

# get unixtimes for start/end of this day
$ date -u -d 'Thu Mar 17 19:02:00 UTC 2022' +%s
1647543720
$ date -u -d 'Fri Mar 18 13:45:00 UTC 2022' +%s
1647611100

$ vibimon_bridge -v history --all --start 1647543720 --end 1647611100 > STDOUT 2> STDERR
```

It should take about 24 hours per observation day, because it's single
threaded and sleeps for 1 second between fetches.

The output is a file tree that looks something like:

```
data/
  ALMA/
    weatherMap_waterVapor_url.csv
    ...
```

## Create a sqlite3 db from downloaded vlbimon data

Using python3,

```
python create_tables.py
python insert_station.py /path/to/vlbimon-bridge/data
```

You should end up with a `vlbimon.db` file. One day of 2022 vlbimon
data is 17 megabytes.

To upload these csv files to the Grafana database, see https://github.com/wumpus/eht-monitor-demo

## Real-time "bridge" from vlbimon to our database

Set up a database (only needed once):
```
$ vlbimon_bridge -v initdb --sqlitedb /var/lib/grafana/live.db
```

Start the bridge:

```
$ vlbimon_bridge -v bridge --start 0 --sqlitedb /var/lib/grafana/live.db > STDOUT 2> STDERR
```

You might find it useful to background the bridge (^Z) and then disown the process (`disown %1`)

While in bridge mode, touching the file ./data/PLEASE-EXIT makes the bridge exit cleanly. This is
useful when updating the bridge software.

## Data size

A year of 2023 data, which includes a lot of pre-and-post observation, is 1.2 gigabytes stored in sqlite.

## Utilities

Several utilities are in the scripts/ directory:

* summarize-sqlite-db.py: checks that column names are reasonable, then summarizes data per station and start/end dates
* sqlite-backup.py: safely backs up a sqlite database while it is being updated
* session-example.py: demonstrates how to use the vlbimon "session" feature to incrementally download new data
* add-column.py: example code for how to add a new column
