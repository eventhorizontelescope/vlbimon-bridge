import yaml
import requests
import os.path
import time
import sys

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
