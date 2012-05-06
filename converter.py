#!/usr/bin/env python
# coding: utf-8

import datetime

import icalendar
import palmFile


class PalmFile(object):
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

    def __init__(self, filename, src_encoding='latin1'):
        self.filename = filename
        self.src_encoding = src_encoding
        self.categories = {}
        self.events = []
        self.raw_data = None

    def export(self, filename):
        if not self.events:
            self.import_file()
        vcal = icalendar.Calendar()
        vcal.add('prodid', "Xelnext palm2iCal converter")
        vcal.add('version', '0.1')

        for e in self.events:
            vcal.add_component(e)

        with open(filename, 'w') as f:
            f.write(vcal.to_ical())

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
        self.raw_data = palmFile.readPalmFile(self.filename)[0]
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
