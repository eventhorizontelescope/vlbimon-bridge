import yaml
import requests
import os.path

'''
example ~/.vlbimonitor-secrets.yaml:
vlbimon1.science.ru.nl:
  basicauth:
  - A Username
  - their-password
'''


def get_auth(server='vlbimon1.science.ru.nl',
             secrets_file='~/.vlbimonitor-secrets.yaml'):
    secrets_file = os.path.expandvars(os.path.expanduser(secrets_file))
    with open(secrets_file) as f:
        conf = yaml.safe_load(f)
    # expect a dict of hostnames
    conf = conf.get(server, {})
    if 'basicauth' in conf:
        return tuple(conf['basicauth'])  # expecting ('username', 'password')
    if 'digestauth' in conf:
        from requests.auth import HTTPDigestAuth
        return HTTPDigestAuth(*conf['digestauth'])  # also ('username', 'password')
    raise ValueError('failed to find auth information in {} for server {}, please check the format'.format(secrets_file, server))


def get_history(server, datafields, observatories, start_timestamp, end_timestamp, auth=None):
    query = '/data/history'
    if not server.startswith('https://'):
        server = 'https://' + server
    params = {
        'observatory': observatories,
        'field': datafields,
        'startTime': int(start_timestamp),
        'endTime': int(end_timestamp),
    }
    resp = requests.get(server+query, params=params, auth=auth)
    if resp.status_code != 200:
        print('whoops! field {} returned {} and:\n'.format(datafields, resp.status_code))
        print(resp.text)
        return None

    # what users expect:
    # None is an error, nothing learned
    # empty dict is no returned points in this timespan
    # dict with points is a valid result

    try:
        j = resp.json()
    except Exception as e:
        print('whoops! failed json decode of', repr(e))
        print('  text is', resp.text)
        return None

    return j


def create_session(server, auth):
    if not server.startswith('https://'):
        server = 'https://' + server
    r = requests.post(server + '/session', auth=auth)
    j = r.json()
    if not r.ok:
        print()
    r.raise_for_status()
    return j['id']


def restore_session(server, sessionid, auth):
    if sessionid is None:
        raise FileNotFoundError('no sessionid')
    if not server.startswith('https://'):
        server = 'https://' + server
    r = requests.patch(server + '/session/' + sessionid, auth=auth)
    if r.status_code == 404:
        raise FileNotFoundError('sessionid has expired')
    if not r.ok:
        print()
    r.raise_for_status()
    return sessionid


def get_sessionid(server, sessionid=None, auth=None):
    try:
        return restore_session(server, sessionid, auth)
    except FileNotFoundError:
        return create_session(server, auth)


def get_snapshot(server, last_snap=None, sessionid=None, auth=None):
    query = '/data/snapshot'
    if not server.startswith('https://'):
        server = 'https://' + server

    if last_snap is not None:
        cookies = {'snap_recvTime': str(last_snap)}
    else:
        cookies = {}
    cookies['sessionid'] = sessionid

    r = requests.get(server + query, cookies=cookies)
    if r.status_code in (401, 403):
        # example: requests.exceptions.HTTPError: 401 Client Error: Unauthorized for url: https://vlbimon2.science.ru.nl/data/snapshot
        print('fetching a new session id after getting a', r.status_code)
        sessionid = get_sessionid(server, auth=auth)
        # do not update last_snap, the next get_snapshot call will not have a gap
        return sessionid, last_snap, {}
    if r.status_code in (429, 503):
        # slow down and service unavailable
        print('slow down', r.status_code, 'sleeping for 10sec')
        return sessionid, last_snap, {}

    try:
        snapshot = r.json()
    except Exception as e:
        print('whoops! failed json decode of', repr(e))
        print('  text is', r.text)
        return sessionid, last_snap, {}

    last_snap = r.cookies.get('snap_recvTime')
    return sessionid, last_snap, snapshot
