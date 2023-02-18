from argparse import ArgumentParser

from . import bootstrap


def main(args=None):
    parser = ArgumentParser(description='vlbimon_bridge command line utilities')
    parser.add_argument('--verbose', '-v', action='count', help='be verbose')
    parser.add_argument('-1', dest='one', action='store_true', help='use vlbimon1 (default is vlbimon2)')
    parser.add_argument('--public', action='store_true', help='process public parameters (year round)')
    parser.add_argument('--private', action='store_true', help='process private parameters (during EHT obs)')
    parser.add_argument('--all', action='store_true', help='process all parameters')
    parser.add_argument('--start', action='store', type=int, help='start time (unixtime integer)')
    parser.add_argument('--end', action='store', type=int, help='end time (unixtime integer)')
    parser.add_argument('--param', action='append', help='param to process (default all)')
    parser.add_argument('--stations', action='append', help='stations to process (default all)')

    cmd = parser.parse_args(args=args)
    return bootstrap.bootstrap(cmd)
