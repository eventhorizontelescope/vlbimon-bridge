# vlbimon-bridge

This code is a bridge from the existing EHT VLBIMonitor database to
a time-series database plus Grafana instance.

Currently, you can use it to download a snapshot (say, a day) of data
from vlbimon.

# Installation

```
git clone https://github.com/wumpus/vlbimon-bridge
pip install .
make download-masterlist
```

# Authentication

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

# Usage

```
$ vlbimon_bridge -h
usage: vlbimon_bridge [-h] [--verbose] [-1] [--start START] [--datadir DATADIR] {history,live} ...

vlbimon_bridge command line utilities

positional arguments:
  {history,live}
    history
    live

options:
  -h, --help         show this help message and exit
  --verbose, -v      be verbose
  -1                 use vlbimon1 (default is vlbimon2)
  --start START      start time (unixtime integer)
  --datadir DATADIR  directory to write output in

$ vlbimon_bridge history -h
usage: vlbimon_bridge history [-h] [--public] [--private] [--all] [--end END] [--param PARAM] [--stations STATIONS]

options:
  -h, --help           show this help message and exit
  --public             process public parameters (year round)
  --private            process private parameters (during EHT obs)
  --all                process all parameters
  --end END            end time (unixtime integer)
  --param PARAM        param to process (default all)
  --stations STATIONS  stations to process (default all)

$ vlbimon_bridge live -h
usage: vlbimon_bridge live [-h]

options:
  -h, --help  show this help message and exit
```

# Downloading VLBIMON data

To copy the first day of the EHT 2022 observation,

```
vibimon_bridge -v --all --start 1647543720 --end 1647611100 > STDOUT 2> STDERR
```

It should take about 24 hours to run, because it's single threaded and sleeps for
1 second between fetches.

# Uploading

See https://github.com/wumpus/eht-monitor-demo

