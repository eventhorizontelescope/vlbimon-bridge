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
usage: vlbimon_bridge [-h] [--verbose] [-1] [--stations STATIONS] [--datadir DATADIR] [--secrets SECRETS] {history,initdb,bridge} ...

vlbimon_bridge command line utilities

positional arguments:
  {history,initdb,bridge}
    history             download historical vlbimon data to csv files
    initdb              initialize a sqlite database
    bridge              bridge data from vlbimon into a sqlite database

options:
  -h, --help            show this help message and exit
  --verbose, -v         be verbose
  -1                    use vlbimon1 (default is vlbimon2)
  --stations STATIONS   stations to process (default all)
  --datadir DATADIR     directory to write output in (default ./data)
  --secrets SECRETS     file containing auth secrets, default ~/.vlbimonitor-secrets.yaml

$ vlbimon_bridge initdb -h
usage: vlbimon_bridge initdb [-h] [--sqlitedb SQLITEDB]

options:
  -h, --help           show this help message and exit
  --sqlitedb SQLITEDB  name of the output database; elsewise, print to stdout

$ vlbimon_bridge history -h
usage: vlbimon_bridge history [-h] [--start START] [--end END] [--all] [--public] [--private] [--param PARAM]

options:
  -h, --help     show this help message and exit
  --start START  start time (unixtime integer)
  --end END      end time (unixtime integer)
  --all          process all public and private parameters
  --public       process public parameters (year round)
  --private      process private parameters (during EHT obs)
  --param PARAM  param to process (default all)

$ vlbimon_bridge bridge -h
usage: vlbimon_bridge bridge [-h] [--start START] [--dt DT] [--sqlitedb SQLITEDB] [--wal WAL]

options:
  -h, --help           show this help message and exit
  --start START        start time (unixtime integer) (0=now) (default reads data/server.json last_snap)
  --dt DT              time between calls, seconds, default=10
  --sqlitedb SQLITEDB  name of the output database; elsewise, print to stdout
  --wal WAL            size of the write ahead log, default 1000 4k pages. 0 to disable.
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

* ts\_param\_bridge_totalLag -- the lag between the most recent timestamped point and now
* ts\_param\_bridge_bridgeLag -- the wall-clock time it took to get a snapshot from vlbimon
* ts\_param\_bridge_points -- the number of points transferred in each 10 second window

## Making a sqlite3 db file visible in Grafana

For this db file to be used by grafana, it should follow these somewhat tricky rules:

* It should be in the directory /var/lib/grafana
* It should NOT be named /var/lib/grafana/grafana.db, because Grafana uses that database
* That directory should be owned by group 'grafana' and be group writable
* The db file should be owned by group 'grafana' and be group writable
* If a user is going to run a bridge (see below), they should be a member of group 'grafana'

## Past database migrations

The directory migrations/ contains an ordered list of past database migrations.

This example assumes that the migration script is migrations/99-foo.py:

* prepare old schema test database for future testing
* * `vlbimon_bridge initdb --sq old.db`
* * cp old.db old.db.save  # just in case

* write code
* * move to a testing virtualenv and a git branch
* * write the migration code, looking at previous examples and using the helper functions
* * update sqlite.py to create the new tables/columns
* * update scripts/summarize-sqlite-db.py for the new tables/columns

* deploy code to the test venv
* * `pip install .` into the test venv

* test code against an old test db
* * python migrations/99-foo.py check old.db
* * python migrations/99-foo.py fix old.db
* * run the bridge for a while

* test code against a new test db
* * `make test-bridge.db`  # tests initdb and sqlite and summarize-sqlite-db
* * check (should say no old seen)
* * fix (should refuse to do anything)
* * `make test-bridge`  # tests bridge operation

* test code against a backup of live.db
* * `python scripts/sqlite-backup.py /var/lib/grafana/live.db live.db`
* * check
* * fix
* * bridge

* commit working code
* * someday we'll have a proper CI script but not yet
* * merge (probably a squash merge)

* deploy
* * switch to the production venv
* * ask the production instance to exit by touching `data/PLEASE-EXIT`
* * `tail -f nohup.out` until you see the actual exit (< 10 seconds)
* * `python scripts/sqlite-backup.py /var/lib/grafana/live.db live.db.pre-migrate`
* * `pip install .` the new software into the production venv
* * `nohup vlbimon_bridge -1 bridge --sq /var/lib/grafana/live.db`
* * update Grafana dashboards that use the old names

## Production bridge

The current production bridge is on the same machine as the ehtcc
grafana instance, owned by Greg.
