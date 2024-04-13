import yaml
import requests
import os.path
import json
import time
import sys

'''
example ~/.vlbimonitor-secrets.yaml:
vlbimon1.science.ru.nl:
  basicauth:
  - A Username
  - their-password
'''


def get_server(two, secrets='~/.vlbimonitor-secrets.yaml', verbose=0):
    if two:
        if verbose:
            print('using vlbimon2 -- no SPT')
        server = 'vlbimon2.science.ru.nl'
    else:
        if verbose:
            print('using vlbimon1')
        server = 'vlbimon1.science.ru.nl'
    return expand_server(server), get_auth(server, secrets=secrets, verbose=verbose)


def expand_server(server):
    if server.startswith('http://'):
        server = server.replace('http://', '', 1)
    if not server.startswith('https://'):
        server = 'https://' + server
    server = server.rstrip('/')
    if server.count('/') != 2:
        raise ValueError('invalid server: '+server)
    return server


def get_auth(server, secrets='~/.vlbimonitor-secrets.yaml', verbose=0):
    secrets = os.path.expandvars(os.path.expanduser(secrets))
    with open(secrets) as f:
        conf = yaml.safe_load(f)
    # expect a dict of hostnames
    conf = conf.get(server, {})
    if 'basicauth' in conf:
        if verbose:
            print('using basicauth and server', server)
        return tuple(conf['basicauth'])  # expecting ('username', 'password')
    if 'digestauth' in conf:
        if verbose:
            print('using digestauth and server', server)
        from requests.auth import HTTPDigestAuth
        return HTTPDigestAuth(*conf['digestauth'])  # also ('username', 'password')
    raise ValueError('failed to find auth information in {} for server {}, please check the format'.format(secrets, server))


def get_history(server, datafields, observatories, start_timestamp, end_timestamp, auth=None, verbose=0):
    query = '/data/history'

    params = {
        'observatory': observatories,
        'field': datafields,
        'startTime': int(start_timestamp),
        'endTime': int(end_timestamp),
    }
    if verbose > 1:
        print('requesting history, server:', server, 'param:', params)
    resp = requests.get(server + query, params=params, auth=auth)
    if resp.status_code != 200:
        print('whoops! field {} returned {} and:\n'.format(datafields, resp.status_code))
        print('  text is', resp.text)
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
    query = '/session'
    while True:
        try:
            r = requests.post(server + query, auth=auth)
            r.raise_for_status()
        except Exception as e:
            print('saw exception', repr(e), 'looping')
            time.sleep(10)
            continue
        try:
            j = r.json()
        except json.JSONDecodeError as e:
            print('saw exception', repr(e), 'looping')
            time.sleep(10)
            continue
        if 'id' in j:
            break
        print('did not see a session id in the return, even though no exceptions were thrown. looping.')
        time.sleep(10)
    return j['id']


def restore_session(server, sessionid, auth):
    if sessionid is None:
        raise FileNotFoundError('no sessionid')
    query = '/session/' + sessionid

    r = requests.patch(server + query, auth=auth)
    if r.status_code == 404:
        raise FileNotFoundError('sessionid has expired')
    if not r.ok:
        print('restore_session saw status', r.status_code)
    r.raise_for_status()
    return sessionid


def get_sessionid(server, sessionid=None, auth=None, verbose=0):
    try:
        if verbose:
            print('attempting to restore session')
        return restore_session(server, sessionid, auth)
    except FileNotFoundError:
        if verbose:
            print('creating a new session after restore did not work')
        return create_session(server, auth)
    except Exception as e:
        print('restore_session got', repr(e), ', creating a new session')
        return create_session(server, auth)


def get_snapshot(server, last_snap=None, sessionid=None, auth=None, verbose=0):
    query = '/data/snapshot'

    if last_snap is not None:
        cookies = {'snap_recvTime': str(last_snap)}
    else:
        cookies = {}
    cookies['sessionid'] = sessionid

    if verbose > 1:
            print('getting snapshot from server', server, 'last snapshot was', last_snap)

    try:
        r = requests.get(server + query, cookies=cookies)
    except Exception as e:
        print('something bad happened ({}). sleeping for 10s.'.format(repr(e)))
        return sessionid, last_snap, {}

    if verbose > 1:
        print('got a snapshot, status_code is', r.status_code)
    if r.status_code in (401, 403):
        # example: requests.exceptions.HTTPError: 401 Client Error: Unauthorized for url: https://vlbimon2.science.ru.nl/data/snapshot
        print('fetching a new session id after getting a', r.status_code)
        sessionid = get_sessionid(server, auth=auth)
        return sessionid, last_snap, {}
    if r.status_code in (429, 503):
        # slow down and service unavailable
        print('slow down', r.status_code, 'sleeping for 10sec')
        return sessionid, last_snap, {}
    if not r.ok:
        print('saw status_code', r.status_code, 'sleeping for 10sec')
        return sessionid, last_snap, {}

    try:
        snapshot = r.json()
    except json.JSONDecodeError as e:
        print('whoops! failed json decode of', repr(e))
        print('  text is', r.text)
        return sessionid, last_snap, {}

    last_snap = r.cookies.get('snap_recvTime')
    return sessionid, last_snap, snapshot
