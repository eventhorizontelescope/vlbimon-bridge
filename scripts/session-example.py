import time
import json

from vlbimon_bridge import client, snapshot, transformer


transformer.init(verbose=1)

server = 'vlbimon2.science.ru.nl'
auth = client.get_auth(server=server)
sid = client.get_sessionid(server, auth=auth)

sid, last_snap, initial = client.get_snapshot(server, sessionid=sid, auth=auth)
print('got in intial data for stations', *initial.keys())

while True:
    sid, last_snap, snap = client.get_snapshot(server, last_snap=last_snap, sessionid=sid, auth=auth)
    print('got snapshot data for stations', *snap.keys())
    flat = snapshot.flatten(snap, add_points=True)
    flat = transformer.transform(flat, verbose=1)
    time.sleep(10)
