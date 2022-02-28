#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Usage:
    perf_test [options] <cmd> <name> <type> <n>

Options:
    -h, --help        Show this page
    --debug            Show debug logging
    --verbose        Show verbose logging
    --no-header
    --only-header
"""
from docopt import docopt
import logging
import sys
import csv
import subprocess
import time

logger = logging.getLogger('perf_test')


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parsed_args = docopt(__doc__, args)
    if parsed_args['--debug']:
        logging.basicConfig(level=logging.DEBUG)
    elif parsed_args['--verbose']:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    writer = csv.DictWriter(sys.stdout, fieldnames=['cmd', 'name', 'type', 'n', 'time'])
    if not parsed_args['--no-header']:
        writer.writeheader()
    if parsed_args['--only-header']:
        return
    start = time.time()
    try:
        subprocess.check_output(parsed_args['<cmd>'], shell=True)
    except BaseException as e:
        print(parsed_args['<cmd>'])
        raise
    end = time.time()
    writer.writerow(dict(cmd=parsed_args['<cmd>'], name=parsed_args['<name>'], type=parsed_args['<type>'], n=parsed_args['<n>'], time=end-start))

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))

