from argparse import ArgumentParser

from . import history
from . import snapshot


def main(args=None):
    parser = ArgumentParser(description='vlbimon_bridge command line utilities')

    parser.add_argument('--verbose', '-v', action='count', help='be verbose')
    parser.add_argument('-1', dest='one', action='store_true', help='use vlbimon1 (default is vlbimon2)')
    parser.add_argument('--start', action='store', type=int, help='start time (unixtime integer)')
    parser.add_argument('--datadir', action='store', default='data', help='directory to write output in')

    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True

    hist = subparsers.add_parser('history', help='')
    hist.add_argument('--public', action='store_true', help='process public parameters (year round)')
    hist.add_argument('--private', action='store_true', help='process private parameters (during EHT obs)')
    hist.add_argument('--all', action='store_true', help='process all parameters')
    hist.add_argument('--end', action='store', type=int, help='end time (unixtime integer)')
    hist.add_argument('--param', action='append', help='param to process (default all)')
    hist.add_argument('--stations', action='append', help='stations to process (default all)')
    hist.set_defaults(func=history.history)

    live = subparsers.add_parser('live', help='')
    live.set_defaults(func=snapshot.snapshot)

    cmd = parser.parse_args(args=args)
    cmd.func(cmd)
