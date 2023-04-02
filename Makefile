download-masterlist: masterlist.json
	wget https://vlbimon1.science.ru.nl/static/masterlist.json

make-types: download-masterlist vlbimon_bridge/vlbimon_types.csv
	python generate_types.py  > vlbimon_types.csv

vlbimon.db:
	python create_tables.py
	python insert_station.py data-e22g18
	mv vlbimon.db vlbimon-e22g18.db
