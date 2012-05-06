#!/usr/bin/env python
# coding: utf-8

import datetime
import optparse
import sys

import icalendar
import palmFile

#from . import __version__
__version__ = '0.1'

class Palm2vCalConverter(object):
    DAYMASK_TRANSLATION = {
        1: 'SU',
        2: 'MO',
        4: 'TU',
        8: 'WE',
        16: 'TH',
        32: 'FR',
        64: 'SA',
    }

    DAY_NAMES = {
        0: 'MO',
        1: 'TU',
        2: 'WE',
        3: 'TH',
        4: 'FR',
        5: 'SA',
        6: 'SU',
    }

    def __init__(self, src_file, src_encoding='cp1252'):
        self.src_file = src_file
        self.src_encoding = src_encoding
        self.categories = {}
        self.events = []
        self.raw_data = None

    def export(self, dst_file):
        if not self.events:
            self.import_file()
        vcal = icalendar.Calendar()
        vcal.add('prodid', "Xelnext palm2vCal converter")
        vcal.add('version', __version__)

        for e in self.events:
            vcal.add_component(e)

        dst_file.write(vcal.to_ical())

    def clean(self, value):
        if isinstance(value, basestring):
            return unicode(value, self.src_encoding)
        else:
            return value

    def mkdate(self, ts, as_date=False):
        dt = datetime.datetime.fromtimestamp(ts)
        if as_date:
            return datetime.date(dt.year, dt.month, dt.day)
        else:
            return dt

    def import_file(self):
        self.raw_data = palmFile.readPalmFileObject(self.src_file)[0]
        for category in self.raw_data['categoryList']:
            self.categories[category['index']] = self.clean(category['longName'])

        for e in self.raw_data['datebookList']:
            self.events.append(self.map_event(e))

    def map_event(self, e):
        """Convert a palmFile event into an icalendar.Event."""

        event = icalendar.Event()
        event.add('dtstart', self.mkdate(e['startTime'], e['untimed']))
        event.add('dtend', self.mkdate(e['endTime'], e['untimed']))
        event.add('summary', self.clean(e['text']))
        if e['note']:
            event.add('description', self.clean(e['note']))
        if e['category']:
            event.add('categories', self.categories[e['category']])

        repeat = e['repeatEvent']

        if repeat['repeatEventFlag'] == 0:
            # No recurrence
            return event

        if repeat.get('dateExceptions'):
            event['exdate'] = icalendar.prop.vDDDLists([self.mkdate(exc, e['untimed']) for exc in repeat['dateExceptions']])

        recur = icalendar.vRecur()

        recur['until'] = self.mkdate(repeat['endDate'], e['untimed'])
        if repeat['interval'] != 1:
            recur['interval'] = repeat['interval']

        if repeat['brand'] == 1:
            # Daily
            recur['freq'] = 'daily'
            # Repeat every sth day of the week
            recur['byday'] = [self.DAY_NAMES[repeat['brandDayIndex']]]
        elif repeat['brand'] == 2:
            # weekly
            recur['freq'] = 'weekly'
            # Mask of week days to use
            # 1 => Sunday, 2 => Monday, 4 => Tuesday, 64 => Saturday
            days_mask = ord(repeat['brandDaysMask'])
            for day_mask, day in self.DAYMASK_TRANSLATION.items():
                days = []
                if days_mask & day_mask:
                    days.append(day)
                if days:
                    recur['byday'] = days

        elif repeat['brand'] == 3:
            # monthly, by day
            recur['freq'] = 'monthly'
            # Day of the week
            recur['byday'] = [self.DAY_NAMES[repeat['brandDayIndex']]]
            # Week of the month
            if repeat['brandWeekIndex'] == 4:
                # Last week of the month
                recur['bysetpos'] = -1
            else:
                recur['bysetpos'] = repeat['brandWeekIndex']
        elif repeat['brand'] == 4:
            # monthly, by date
            recur['freq'] = 'monthly'
            # Day in the month
            recur['bymonthday'] = repeat['brandDayNumber']

        elif repeat['brand'] == 5:
            # yearly, by date
            recur['freq'] = 'yearly'
            # Day in the month
            recur['bymonthday'] = repeat['brandDayNumber']
            # Month in the year
            recur['bymonth'] = repeat['brandMonthIndex'] + 1

        elif repeat['brand'] == 6:
            # yearly, by day
            recur['freq'] = 'yearly'

        event['rrule'] = recur

        return event


def main(argv):
    usage = """usage: %prog [options] [from_file [to_file]]

Parse file <from_file> and write it to <to_file>.
If <to_file> is either '-' or omitted, %prog will write to stdout.
If <from_file> is either '-' or omitted, %prog will read from stdin.
"""
    parser = optparse.OptionParser(usage=usage, version=__version__)
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
        conv = Palm2vCalConverter(src_file, src_encoding=opts.encoding)
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
