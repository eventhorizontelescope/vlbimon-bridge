download-masterlist:
	wget https://vlbimon1.science.ru.nl/static/masterlist.json

make-types:
	python scripts/generate_types.py  > vlbimon_types.csv

vlbimon.db:
	vlbimon_bridge initdb --sqlitedb vlbimon-e22g18.db --wal 0
	python insert_station.py vlbimon-e22g18.db data-e22g18

test.db:
	vlbimon_bridge -v -v initdb --sqlitedb test.db

test-bridge:
	vlbimon_bridge -v -v bridge --sqlitedb test.db
