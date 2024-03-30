# vlbimon-bridge

This code is a bridge from the EHT VLBI Monitor database to a
time-series database (currently sqlite) that feeds a Grafana instance.
The reason for this additional database is to make sure that the load
on the vlbimonitor database remains low, no matter how many users are
displaying Grafana graphs.

vlbimon-bridge can be used in two modes:

* Downloading historical data to .csv files, and then inserting it into a database
* Real-time "bridging" of data from vlbimon to a database

## Transformers

Transformers run on the data between being downloaded from vlbimon and
being inserted into sqlite. The main reason they exist is that most of
us are more comfortable with python than SQL or javacript, and also
there are some data tranformations which are difficult to express in
SQL and javascript. The main minus is that while you can develop a
transformer by downloading some data and testing on that data locally,
it can only be deployed to production by the person running the
production bridge. Open a pull request once you're happy with your
transformer. Open an issue in this sub if you have questions about
downloading data or developing transformers.

## Installation

```
git clone https://github.com/wumpus/vlbimon-bridge
cd vlbimon-bridge
pip install .
make init  # downloads schema from vlbimon server
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

It should take about 24 hours per observation day, intentionally slow
from being single threaded and sleeping for 1 second between fetches.

The output is a file tree that looks something like:

```
data/
  ALMA/
    weatherMap_waterVapor_url.csv
    ...
```

## Create a sqlite3 db from downloaded vlbimon data

Create an empty database:

```
vlbimon_bridge -v initdb --sqlitedb data-e99a99.db
```

and then XXX I need to repair this code:

```
python insert_station.py /path/to/vlbimon-bridge/data  # XXX where is this script now?
```

The sqlite3 size of one day of 2022 vlbimon data is 17 megabytes.

## Real-time "bridge" from vlbimon to our database

The first time, create a database. The above tricky rules need to be followed
for the group permission of the user and the directory /var/lib/grafana:

```
$ vlbimon_bridge -v initdb --sqlitedb /var/lib/grafana/live.db
```

Start the bridge, first the debugging-friendly version:

```
$ vlbimon_bridge -v bridge --start 0 --sqlitedb /var/lib/grafana/live.db
```

`--start 0` is optional. In the above example it means to start the dataset now.
In this next example, the bridge software will use a cached start value to prevent
a gap in the dataset, as long as the last transfer was not too long in the past.

The daemon version (no debugging, no `--start`):

```
$ nohup vlbimon_bridge bridge --sqlitedb /var/lib/grafana/live.db &
$ disown %1  # or whatever the proper jobspec is
```

While in bridge mode, touching the file ./data/PLEASE-EXIT makes the bridge exit cleanly. This is
useful when updating the bridge software:

* touch the data/PLEASE-EXIT file
* wait for the bridge to exit, for example by tailing nohup.out
* update the software (perhaps `pip install .`)
* restart the bridge
* Thanks to the clean exit, the dataset will have no gap

## Data size

A year of 2023 data, which includes a lot of pre-and-post observation, is 1.2 gigabytes stored in sqlite.

## Utilities

Several utilities are in the scripts/ directory:

* summarize-sqlite-db.py: checks that column names are reasonable, then summarizes which stations are reporting which parameters, and start-end dates by parameter
* sqlite-backup.py: safely backs up a sqlite database while it is being updated
* session-example.py: demonstrates how to use the vlbimon "session" feature to incrementally download new data.
* add-column.py: example code for how to add a new column

## Monitoring the bridge itself

As the bridge runs it creates two timeseries, one for "lag" (how many seconds the
fetch of vlbimon data took) and one for how many data points were in each update,
per station and the sum over all stations.

## Making a sqlite3 db file visible in Grafana

For this db file to be used by grafana, it should follow these somewhat tricky rules:

* It should be in the directory /var/lib/grafana
* It should NOT be named /var/lib/grafana/grafana.db, because Grafana uses that database
* That directory should be owned by group 'grafana' and be group writable
* The db file should be owned by group 'grafana' and be group writable
* If a user is going to run a bridge (see below), they should be a member of group 'grafana'

## Past database migrations

This is an ordered list:

* scripts/fix-bug-azelalt.py
* scripts/create-remo.py

## Production bridge

The current production bridge is on the same machine as the ehtcc
grafana instance, owned by Greg.
