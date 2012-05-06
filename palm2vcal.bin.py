#!/usr/bin/env python
# coding: utf-8


import optparse
import sys

import palm2vcal


def main(argv):
    usage = """usage: %prog [options] [from_file [to_file]]

Parse file <from_file> and write it to <to_file>.
If <to_file> is either '-' or omitted, %prog will write to stdout.
If <from_file> is either '-' or omitted, %prog will read from stdin.
"""
    parser = optparse.OptionParser(usage=usage, version=palm2vcal.__version__)
    parser.add_option('-e', '--encoding', dest='encoding', default='cp1252',
        help="Read input with ENCODING encoding")
    parser.add_option('-v', '--verbose', dest='verbose', default=False,
        action='store_true', help="More verbose messages.")

    opts, args = parser.parse_args()

    if len(args) > 2:
        parser.error("At most 2 arguments are allowed, from and to.")

    if len(args) == 2:
        src, dst = args
    elif len(args) == 1:
        # Assume output do stdout
        src, dst = args[0], '-'
    else:
        src, dst = '-', '-'

    if src == '-':
        src_file = sys.stdin
    else:
        src_file = open(src, 'rb')

    try:
        conv = palm2vcal.Palm2vCalConverter(src_file, src_encoding=opts.encoding)
        conv.import_file()
    finally:
        if src != '-':
            src_file.close()

    if dst == '-':
        dst_file = sys.stdout
    else:
        dst_file = open(dst, 'wb')

    try:
        conv.export(dst_file)
    finally:
        if dst != '-':
            dst_file.close()

    if opts.verbose:
        logfile = sys.stderr if dst == '-' else sys.stdout
        srcfname = 'stdin' if src == '-' else '%r' % src
        dstfname = 'stdout' if dst == '-' else '%r' % dst
        logfile.write("Written %d events from %s to %s.\n" %
            (len(conv.events), srcfname, dstfname))


if __name__ == '__main__':
    main(sys.argv)
