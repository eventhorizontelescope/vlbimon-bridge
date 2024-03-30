.PHONY: test-bridge

DR2024_START='00:20 25 Jan 2023 UTC'
DR2024_END='01:42 25 Jan 2023 UTC'
DR_NAME=e24j25
START_TS := $(shell date -d $(DR2024_START) +%s)
END_TS :=  $(shell date -d $(DR2024_END) +%s)

init: masterlist.json vlbimon_types.csv

masterlist.json:
	# does not require auth
	# sort order is not stable
	wget https://vlbimon1.science.ru.nl/static/masterlist.json

vlbimon_types.csv: masterlist.json
	python scripts/generate-types.py  > vlbimon_types.csv

data-e24j25:
	echo 'this will take about 2.5 hours for 2 hours of dress rehearsal data'
	echo start $(START_TS) end $(END_TS)
	vlbimon_bridge -v --datadir ./data-e24j25 history --start $(START_TS) --end $(END_TS) --all
	echo 'data size should be 8.1 megagbytes'
	du -sh data-e24j25
	echo done

vlbimon-e24j25.db:
	# no WAL because this is going to be a bulk insert
	vlbimon_bridge initdb --sqlitedb vlbimon-e24j25.db
	# XXX where is this script now?
	python insert_station.py vlbimon-e24j25.db data-e24j25

test-bridge.db:
	echo creating db
	vlbimon_bridge -v -v initdb --sqlitedb test-bridge.db
	echo summarizing db
	python scripts/summarize-sqlite-db.py test-bridge.db

test-bridge: test-bridge.db
	vlbimon_bridge -v -v --data datatest bridge --sqlitedb test-bridge.db --start 0
