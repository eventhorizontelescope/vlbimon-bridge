import time
import os
import os.path

from . import client
from . import utils


def select_cadence(cmd, value):
    cadence = None
    c_pub = value.get('cadence', {}).get('public')
    c_priv = value.get('cadence', {}).get('private')
    if cmd.public:
        cadence = c_pub
    elif cmd.private:
        cadence = c_priv
    elif cmd.all:
        cadence = c_pub or c_priv

    if cadence is None:
        return None
    if not cadence:
        cadence = 8640  # 1/10 day in seconds
    return int(cadence)


def history(cmd):
    verbose = cmd.verbose
    datadir = cmd.datadir.rstrip('/')
    secrets = cmd.secrets

    if cmd.one:
        if verbose:
            print('using vlbimon1')
        server = 'https://vlbimon1.science.ru.nl/'
        auth = client.get_auth(secrets=secrets, verbose=verbose)
    else:
        if verbose:
            print('using vlbimon2')
        server = 'https://vlbimon2.science.ru.nl/'
        auth = client.get_auth('vlbimon2.science.ru.nl', secrets=secrets, verbose=verbose)

    stations, parameters = utils.read_masterlist()
    utils.comment_on_masterlist(stations, parameters, verbose=verbose)
    metadata = utils.read_metadata(stations, metadir=datadir)

    stations = cmd.stations or stations

    for station in stations:
        if verbose:
            print(station+':')
        for param, value in parameters.items():
            if cmd.param and param not in cmd.param:
                continue
            metadata = utils.read_metadata(stations, station=station, metadir=datadir, verbose=verbose)
            dirname = datadir + '/' + station
            os.makedirs(dirname, exist_ok=True)
            fout = dirname + '/' + param + '.csv'

            cadence = select_cadence(cmd, value)
            if cadence is None:
                continue

            if verbose:
                print(fout+':')

            cadence *= 100
            orig_cadence = cadence

            # note that this loop ignores last_tried and last_seen
            tee = cmd.start
            while tee < cmd.end:
                ts = tee
                tee += cadence
                te = min(cmd.end, ts + cadence)
                resp_json = client.get_history(server, param, station, ts, te, auth=auth, verbose=verbose)

                # None = error, nothing learned
                # {} = valid but no data for interval. update metadata and last_tried
                # valid data... update both last_tried and last_seen

                if resp_json is None:
                    cadence *= 1.5
                    cadence = int(cadence)
                    continue

                if param not in metadata[station]:
                    metadata[station][param] = {}

                metadata[station][param]['last_tried'] = te
                if len(resp_json) == 0:
                    cadence *= 1.5
                    cadence = int(cadence)
                    continue

                if len(resp_json) > 5:
                    # there's a bug where we get a single point before "start"
                    # with every single query
                    # don't adjust the cadence unless we got a lot of points
                    cadence = orig_cadence

                points = resp_json[station][param]
                utils.debug_cadence(points, station=station, param=param, verbose=verbose)
                if len(resp_json) > 0:
                    last_seen = points[-1][0]
                    if last_seen > te:
                        print('whoops. got a point for {} {} in the future'.format(station, param))
                    if last_seen == 946684800:  # yes, it's an int: 'Sat Jan  1 00:00:00 UTC 2000'
                        print('whoops: 2000 BUG seen, backing up one')
                        points.pop()
                        try:
                            last_seen = points[-1][0]  # may crash
                        except Exception:
                            last_seen = None
                    if last_seen is not None:
                        metadata[station][param]['last_seen'] = last_seen

                with open(fout, 'a') as fd:
                    for t, v in points:
                        if isinstance(v, str):
                            v = v.strip()
                        print('{},{}'.format(t, v), file=fd)

                utils.write_metadata(metadata, station=station, metadir=datadir, verbose=verbose)

                time.sleep(1)
