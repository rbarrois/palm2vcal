"""
Python module that parses palm files

The files are parsed into list/dictionary data structure that mirrors
the structure of the palm file.

Thanks to Scott Leighton who provided the Palm File format at
http://www.geocities.com/Heartland/Acres/3216/palmrecs.htm

Usage

import palmFile.py
fileStruct = palmFile.readPalmFile(<fileName>)

the structure you get back mirrors the file structure. I use
import pprint
pprint.pprint(fileStruct)
to make sense of the data I get back
see printAWeekWorthOfCalendar and printAllNames for examples

to write this information back to a file, use
palmFile.writePalmFile(<fileName>, <fileType>, fileStruct)
"""

"""
Author: jeffweb@mikels.cc
    (since Version 0.4)

Original Author: atotic@yahoo.com


Version 0.5
Date: 04/08/2004
Added:
    Major additions to enable the writePalmFile() function.
    writePalmFile(fileName, fileData)
        writes a palm desktop .dat format file containing fileData.
        fileType is determined from fileData[0]['versionTag']
        fileData must be an appropriately formed list / dictionary
        of the same format returned by readPalmFile

Version 0.4
Date: 03/28/2004
Added:
    getNextRepeatedEvent(event)
        computes the next occurrence of a repeated event and returns it as an event dictionary
    printAWeekWorthOfCalendar(calendar, traceRepeats=False)
        prints to stdout a week's worth of upcoming events.
        if traceRepeats is 1, then this function will also look for upcoming
        occurrences of repeated events
    getEvents(calendar)
        returns a dictionary of events when given a palm datebook fileStruct as calendar
    getUpcomingEvents(calendar, daysAhead, traceRepeats=False)
        returns a list of events from calendar (palm datebook fileStruct) from the present moment
        up to daysAhead number of days into the future. If traceRepeats is 1, then function will
        also look for upcoming occurrences of repeated events.


Version 0.3
Date: 12/12/03
Patch for readRepeatEvent, from John Lim (Rainlendar guy)

Date: Apr 24, 2003
Version: 0.2: fixed dateExceptionCount parsing

Date: 11/21/2002
Version: 0.1, my first Python code

It works on my machine, Python 2.2, I have not tried it on any others

Terminology used in coding:
record - a list of items in a known predefined format, not composed of fields
        each record read has a HEADERDEF defined in this file that describes it
frecord - a special record, where each item is a *field*
field - fields have type & data. The labels are implicit in their position
        and are defined in this file as a list
items - basic units we know how to read: byte/short/long/, etc
"""

# Globals
readDebug = False
writeDebug = False



# Address book defines

"""
HEADERDEF lists format
HEADERDEF are data that represent the file format.
I've tried to make all parsing data driven, and HEADERDEF structs
describe the grammar. When data to be read go beyound what HEADERDEF
defines, 3rd column provides the name Python to be executed.

headerDef tuple columns format
col 1 property name
col 2 type short, long, palm cstring, record, frecord
3 additional argument:
    if type in col 2 is record, the name of the entry that defines the struct count
    if type in col 2 is frecord, the python code to execute
"""

"""See HEADERDEF lists format above"""
addressHeaderDef = (
    ("versionTag", "long"),
    ("fileName", "cstring"),
    ("tableString", "cstring"),
    ("nextFree", "long"),
    ("categoryCount","long"),
    ("categoryList", "record", "addressCategoryEntryDef", "categoryCount"),
    ("resourceID", "long"),
    ("fieldsPerRow", "long"),
    ("recIDPos", "long"),
    ("recStatus", "long"),
    ("placementPos", "long"),
    ("fieldCount", "short"),
    ("fieldEntryList", "record", "addressSchemaFieldDef", "fieldCount"),
    ("numEntries", "long"),
    ("addresses", "frecord","addressEntryFields")
    )

"""See HEADERDEF lists format above"""
addressCategoryEntryDef = (
    ("index", "long"),
    ("id", "long"),
    ("dirtyFlag", "long"),
    ("longName", "cstring"),
    ("shortName", "cstring")
    )

"""See HEADERDEF lists format above"""
addressSchemaFieldDef = (
    ("fieldEntryType", "short"),
    )

"""See HEADERDEF lists format above"""
addressEntryFields = (
        "recordID",
        "status",
        "position",
        "lastName",
        "firstName",
        "title",
        "companyName",
        "phone1LabelID",
        "phone1Text",
        "phone2LabelID",
        "phone2Text",
        "phone3LabelID",
        "phone3Text",
        "phone4LabelID",
        "phone4Text",
        "phone5LabelID",
        "phone5Text",
        "address",
        "city",
        "state",
        "zip",
        "country",
        "note",
        "private",
        "category",
        "custom1Text",
        "custom2Text",
        "custom3Text",
        "custom4Text",
        "displayPhone"
)




# Calendar defines

"""See HEADERDEF lists format above"""
calendarHeaderDef = (
    ("versionTag", "long"),
    ("fileName", "cstring"),
    ("tableString", "cstring"),
    ("nextFree", "long"),
    ("categoryCount","long"),
    ("categoryList", "record", "addressCategoryEntryDef", "categoryCount"),
    ("resourceID", "long"),
    ("fieldsPerRow", "long"),
    ("recIDPos", "long"),
    ("recStatus", "long"),
    ("placementPos", "long"),
    ("fieldCount", "short"),
    ("fieldEntry", "record", "addressSchemaFieldDef", "fieldCount"),
    ("numEntries", "long"),
    ("datebookList", "frecord","calendarEntryFields")
)

calendarEntryFields = (
    "recordID",
    "status",
    "position",
    "startTime",
    "endTime",
    "text",
    "duration",
    "note",
    "untimed",
    "private",
    "category",
    "alarmSet",
    "alarmAdvUnits",
    "alarmAdvType",
    "repeatEvent"
)



###
# Generic reading and writing routines
# (not to be accessed by user)
###

import struct

def readCString(f):
    """Read in a Palm-format string."""
    
    """
    String docs off the net:
    Strings less than 255 bytes are stored with the length specified in the first byte followed by the actual string. 
    Zero length strings are stored with a 0x00 byte.
    Strings 255 bytes or longer are stored with a flag byte set to 0xFF
    followed by a short (2*Byte) that specifies the length of the string, followed by the actual string. 
    """
    retVal = None
    (firstByte, ) = struct.unpack("B", f.read(1))
    if firstByte == 0x0 :
        retVal = "";
    elif firstByte == 0xFF:
        (length, ) = struct.unpack("H", f.read(2))
        retVal = f.read(length)
    else: # length was in first byte
        retVal = f.read(firstByte)
    return retVal

def writeCString(f, s):
    """Writes string to Palm .dat file"""
    if writeDebug:
        print '---------------------------------------'
        print 'WRITE CSTRING'
        print s
        print '---------------------------------------'
    length = len(s)
    if length >= 255:
        format = "<BH" + str(length) + "s"
        f.write(struct.pack(format, 0xFF, int(length), s))
    else:
        format = "<B" + str(length) + "s"
        f.write(struct.pack(format, int(length), s))

def readShort(f):
    """Read unsigned 2 byte value from a file f."""
    (retVal,) = struct.unpack("<H", f.read(2))
    return retVal
    
def writeShort(f, n):
    if writeDebug:
        print '---------------------------------------'
        print 'WRITE SHORT'
        print n
        print '---------------------------------------'
    f.write(struct.pack("<H", n))

def readLong(f):
    """Read unsigned 4 byte value from a file f."""
    (retVal,) = struct.unpack("<L", f.read(4))
    return retVal

def writeLong(f, n):
    if writeDebug:
        print '---------------------------------------'
        print 'WRITE LONG'
        print n
        print '---------------------------------------'
    f.write(struct.pack("<L", n))
    
def readFloat(f):
    """Read float (4 bytes) from a file f."""
    (retVal,) = struct.unpack("<f", f.read(4))
    return retVal

def writeFloat(f, n):
    if writeDebug:
        print '---------------------------------------'
        print 'WRITE FLOAT'
        print n
        print '---------------------------------------'
    f.write(struct.pack("<f", n))
    
def readRepeatEvent(f):
    """Read RepeatEvent, a hacky palm data structure

    must be read programatically due to randomness of the data structure
    """
    event = {};

    # Exceptions
    event['dateExceptionCount'] = readShort(f)
    dateExceptions = [];
    for i in range(event['dateExceptionCount']):
        dateExceptions.append(readLong(f))
    if len(dateExceptions) > 0:
        event['dateExceptions'] = dateExceptions

    # Repeating
    event['repeatEventFlag']= readShort(f)
    if event['repeatEventFlag'] == 0x0:
        # No repeat, return.
        return event

    if event['repeatEventFlag'] == 0xFFFF:
        classRecord = {}
        classRecord['constant'] = readShort(f)
        classRecord['nameLength'] = readShort(f)
        classRecord['name'] = f.read(classRecord['nameLength'])
        event['classRecord'] = classRecord
    
    event['brand'] = readLong(f)
    event['interval'] = readLong(f)
    event['endDate'] = readLong(f)
    event['firstDayOfWeek'] = readLong(f)
    if event['brand'] in (1L, 2L, 3L):
        event['brandDayIndex'] = readLong(f)
    if event['brand'] == 2L:
        event['brandDaysMask'] = f.read(1)
    if event['brand'] == 3L:
        event['brandWeekIndex'] = readLong(f)
    if event['brand'] in (4L, 5L):
        event['brandDayNumber'] = readLong(f)
    if event['brand'] == 5L:
        event['brandMonthIndex'] = readLong(f)
    return event

def writeRepeatEvent(f, repeatEventDetails):
    """Write RepeatEvent.
    """
    if writeDebug:
        print '---------------------------------------'
        print 'WRITING REPEAT EVENT'
        import pprint
        pprint.pprint(repeatEventDetails)
        print '---------------------------------------'
    writeShort(f, repeatEventDetails['dateExceptionCount'])

    if repeatEventDetails['dateExceptionCount'] != 0:
        for dateException in repeatEventDetails['dateExceptions']:
            writeLong(f, dateException)
    writeShort(f, repeatEventDetails['repeatEventFlag'])

    if repeatEventDetails['repeatEventFlag'] == 0x0:
        return
    if repeatEventDetails['repeatEventFlag'] == 0xFFFF:
        classRecord = repeatEventDetails['classRecord']
        writeShort(f, classRecord['constant'])
        writeShort(f, classRecord['nameLength'])
        f.write(classRecord['name'])

    writeLong(f, repeatEventDetails['brand'])
    writeLong(f, repeatEventDetails['interval'])
    writeLong(f, repeatEventDetails['endDate'])
    writeLong(f, repeatEventDetails['firstDayOfWeek'])
    if repeatEventDetails['brand'] in (1L, 2L, 3L):
        writeLong(f, repeatEventDetails['brandDayIndex'])
    if repeatEventDetails['brand'] == 2L:
        f.write(repeatEventDetails['brandDaysMask'])
    if repeatEventDetails['brand'] == 3L:
        writeLong(f, repeatEventDetails['brandWeekIndex'])
    if repeatEventDetails['brand'] in (4L, 5L):
        writeLong(f, repeatEventDetails['brandDayNumber'])
    if repeatEventDetails['brand'] == 5L:
        writeLong(f, repeatEventDetails['brandMonthIndex'])
    return
    
def readField(f, fieldType):
    """Read palm record from a file f.
    
    fieldType -- integer specifying the palm field type
    """
    if readDebug:
        print '-----------------------------------'
        print 'READING FIELD'
        print 'file:', f
        print 'fieldType:', fieldType
    retVal = None
    if fieldType == 0: # none
        retVal = None
    elif fieldType == 1: # integer
        retVal = readLong(f)
    elif fieldType == 2: # float
        retVal = readFloat(f)
    elif fieldType == 3: # date
        retVal = readLong(f)
    elif fieldType == 4: # alpha
        raise NotImplementedError()
    elif fieldType == 5: # cstring
        readLong(f) # padding
        retVal = readCString(f)
    elif fieldType == 6: # boolean
        retVal = (readLong(f) != 0)
    elif fieldType == 7: # bit flag
        retVal = readLong(f)
    elif fieldType == 8: # repeat event, bad hack, bad
        retVal = readRepeatEvent(f)
    else:
        raise ValueError()
    if readDebug:
        import pprint
        pprint.pprint(retVal)
    
    return retVal

def writeField(f, fieldType, s):
    """Write palm field to a file.
    
    fieldType -- integer specifying the palm field type
    """
    if writeDebug:
        print '---------------------------------------'
        print 'WRITING FIELD'
        print 'fieldType:', fieldType
        print 'value:', s
        print '---------------------------------------'
    if fieldType == 0: # none
        pass
    elif fieldType == 1: # integer
        writeLong(f, s)
    elif fieldType == 2: # float
        writeFloat(f, s)
    elif fieldType == 3: # date
        writeLong(f, s)
    elif fieldType == 4: # alpha
        raise NotImplementedError()
    elif fieldType == 5: # cstring
        writeLong(f, 0) # padding
        writeCString(f, s)
    elif fieldType == 6: # boolean
        if s:
            s = 1
        else:
            s = 0
        writeLong(f, s)
    elif fieldType == 7: # bit flag
        writeLong(f, s)
    elif fieldType == 8: # repeat event, bad hack, bad
        writeRepeatEvent(f, s)
    else:
        raise ValueError()

def readFRecords(f, fileSoFar, labels):
    """reads a list of frecords from file f
    
    returns -- a list of records
    fileSoFar -- dictionary of data read so far, used to get the number
                of records to read
    labels -- a list of labels for the fields
    """
    if readDebug:
        print '---------------------------------'
        print 'READING FRECORDS'
        print 'fileSoFar'
        import pprint
        pprint.pprint(fileSoFar)

    fieldsPerRecord = fileSoFar['fieldCount']
    # make sure that declared 
    if fieldsPerRecord != len(labels):
        raise ValueError()

    numberOfRecords = fileSoFar['numEntries'] / fieldsPerRecord;
#    print "reading", str(numberOfRecords), "records"
    entries = []
    for i in range(numberOfRecords):
#        print "reading record", str(i)
        newEntry = {}
        for j in labels:
            fieldType = readLong(f)
            newEntry[j] = readField(f, fieldType)
        entries.append(newEntry)
#    print "done with", str(numberOfRecords), "records"
    return entries

def writeFRecords(f, fieldEntryList, labels, list):
    """writes a list of frecords to file f

    fieldEntryList -- a list describing the order of field types in each record
    list -- a list of records to write
    labels -- a list of labels for the fields
    """
    if writeDebug:
        print '---------------------------------------'
        print 'WRITING FRECORDS'
        import pprint
        print '\nfieldEntryList'
        pprint.pprint(fieldEntryList)
        print '\nlabels'
        pprint.pprint(labels)

    if len(fieldEntryList) != len(labels):
        raise ValueError()

    for item in list:
        if writeDebug:
            print '\nitem to write'
            import pprint
            pprint.pprint(item)
        for i in range(len(labels)):
            fieldType = fieldEntryList[i]['fieldEntryType']
            if writeDebug:
                print 'in frecords, attempting to write field:'
                print 'f:', f
                print 'fieldType:', fieldType
                print 'label:', labels[i]
                import pprint
                pprint.pprint(item[labels[i]])
            writeLong(f, fieldType)
            writeField(f, fieldType, item[labels[i]])

def readRecords(f, fileFormat, howMany=1, versionTag=None):
    """reads a list of objects from a file f
    
    fileFormat -- HEADERDEF of what format looks like
    howMany -- how many records to read
    returns a list of howMany dictionaries: [ {d1}, .... {dN}]
    """
    retVal = []
    #    print "entering", str(fileFormat[0]);
    for i in range(howMany):
        if readDebug:
            print '------------------------------'
            print 'READING RECORDS'
            print 'retVal:'
            import pprint
            pprint.pprint(retVal)
        entry = {}
        for fieldDef in fileFormat:
            if fieldDef[0] == "versionTag" and versionTag is not None:
                entry[fieldDef[0]] = versionTag
            elif fieldDef[1] == "long":
                entry[fieldDef[0]] = readLong(f)
            elif fieldDef[1] == "short":
                entry[fieldDef[0]] = readShort(f)
            elif fieldDef[1] == "cstring":
                entry[fieldDef[0]] = readCString(f)
            elif fieldDef[1] == "record":
                entry[fieldDef[0]] = readRecords(f, eval(fieldDef[2]), entry[fieldDef[3]])
            elif fieldDef[1] == "frecord":
                entry[fieldDef[0]] = readFRecords(f, entry, eval(fieldDef[2]))
            else:
                raise AssertionError()
        retVal.append(entry);
    #    print "returning", str(fileFormat[0])
    return retVal

def writeRecords(f, fileFormat, list):
    """reads a list of objects from a file f
    
    fileFormat -- HEADERDEF of what format looks like
    list -- a list of dictionaries to write as palm records
    """
    if writeDebug:
        print '\n----------------------------\nWRITING RECORDS'
        import pprint
        print 'fileFormat:'
        pprint.pprint(fileFormat)
        print '\nlist:'
        pprint.pprint(list)
    #for i in range(len(list)):
    for item in list:
        for fieldDef in fileFormat:
            if writeDebug:
                print '\nfieldDef:'
                print fieldDef
            if fieldDef[1] is "long":
                writeLong(f, item[fieldDef[0]])
            elif fieldDef[1] is "short":
                writeShort(f, item[fieldDef[0]])
            elif fieldDef[1] is "cstring":
                writeCString(f, item[fieldDef[0]])
            elif fieldDef[1] is "record":
                if writeDebug:
                    print 'WILL WRITE RECORDS'
                writeRecords(f=f, fileFormat=eval(fieldDef[2]), list=item[fieldDef[0]])
                if writeDebug:
                    print 'BACK FROM WRITING RECORDS'
            elif fieldDef[1] is "frecord":
                if writeDebug:
                    print 'WILL WRITE FRECORDS'
                writeFRecords(f=f, fieldEntryList=item['fieldEntry'], labels=eval(fieldDef[2]), list=item[fieldDef[0]])
                if writeDebug:
                    print 'BACK FROM WRITING FRECORDS'
            else:
                raise AssertionError()


######################
# MAIN FUNCTIONS
######################

def readPalmFile(fileName):
    """ Read in a Palm fileName with a specified format
    
    The type of the file is determined automatically by reading
    the first four bytes
    fileFormat -- different files have different formats (address book, calendar...)
                [abHeaderDef | calHeaderDef]
    """
    retVal = None
    try:
        palmFile = open(fileName, "rb")
    except IOError:
        print "Palm file", fileName, "cannot be opened\n\n"
        raise

    try:
        result = readPalmFileObject(palmFile)
    finally:
        palmFile.close()
    return result

def readPalmFileObject(file_obj):
    try:
        sig = file_obj.read(4)
#        file_obj.seek(0)
        if sig == "\x00\x01BA": # address book
            fileFormat = addressHeaderDef 
        elif sig == "\x00\x01BD": # datebook (calendar)
            fileFormat = calendarHeaderDef
        else:
            print "Unknown file format ", sig
            raise ValueError()
        retVal = readRecords(file_obj, fileFormat, 1, versionTag=sig)
    except IOError:
        print "Unexpected error while reading Palm file"
        raise
    return retVal

def writePalmFile(fileName, fileData):
    '''Writes a palm desktop file
    '''
    if writeDebug:
        print '---------------------------------------'
        print 'ATTEMPTING TO WRITE PALM FILE\nFILE:', fileName
        print 'fileType:', fileType
        print 'fileData:\n'
        import pprint
        pprint.pprint(fileData)
    """ Write a Palm fileName with a specified format
    
    The type of the file is determined automatically by reading
    the first four bytes
    fileFormat -- different files have different formats (address book, calendar...)
                [abHeaderDef | calHeaderDef]
    """
    fileType = fileData[0]['versionTag']
    sig = struct.pack("L", fileType)
    if not (sig == '\x00\x01BA' or sig == '\x00\x01BD'):
        print "Unknown file format ", sig
        raise ValueError()

    try:
        palmFile = open(fileName, "wb")
    except IOError:
        print "Palm file", fileName, "cannot be opened\n\n"
        raise
    try:
        #palmFile.write(sig)
        if sig == "\x00\x01BA": # address book
            fileFormat = addressHeaderDef 
        elif sig == "\x00\x01BD": # datebook (calendar)
            fileFormat = calendarHeaderDef
        else:
            print "Unknown file format ", sig
            raise ValueError()
        writeRecords(palmFile, fileFormat, fileData)
    except IOError:
        print "Unexpected error while writing Palm file"
        raise
    if palmFile : palmFile.close()

def printAllNames(adBook):
    """print all names in the address book

    demo of walking the address book structure
    """
    addressDict = adBook[0]
    addresses = addressDict["addresses"]
    for address in addresses:
        print address["firstName"], address["lastName"]

def printCalendar(calendar, days=7, traceRepeats=False):
    """demo of walking the calendar data structure

    prints all events a week from now    
    """
    import time 
    print "Your schedule next week:"
    events = getUpcomingEvents(calendar, days, traceRepeats)
    for event in events:
        if event['untimed']:
            print time.strftime("%x ***", time.localtime(event['startTime'])), event['text']
        else :
            print time.strftime("%c-", time.localtime(event['startTime'])), time.strftime("%X", time.localtime(event['endTime'])), event['text']
        if event['note']: print event['note']

def getEvents(calendar):
    return calendar[0]['datebookList']

def getUpcomingEvents(calendar, daysAhead, traceRepeats=False):
    #returns a list of event dictionaries from now until daysAhead days from now
    import time
    calendarDict = calendar[0]
    dateList = calendarDict['datebookList'] #we don't want to change the original calendar so we create a copy
    startTime = time.time();
    endTime = startTime + (daysAhead * 60 * 60 * 24) # converts daysAhead to seconds
    retVal = []
    #print 'Checking for events between', time.localtime(startTime),'and', time.localtime(endTime)
    for event in dateList:
        newEvent = event.copy()
        if newEvent['startTime'] > startTime and newEvent['startTime'] < endTime:
            #print 'Adding [', newEvent['text'], '] [', time.localtime(newEvent['startTime']), ']'
            #pprint.pprint(event)
            #print '\n\n'
            retVal.append(newEvent.copy())
        if traceRepeats and newEvent['repeatEvent']['repeatEventFlag'] and newEvent['repeatEvent']['endDate'] > startTime:
            newEvent = getNextRepeatedEvent(newEvent)
            #print 'Looking [', newEvent['text'],'] [', time.localtime(newEvent['startTime']),']'
            while newEvent['startTime'] < startTime:
                newEvent = getNextRepeatedEvent(newEvent)
                #print 'Looking [', newEvent['text'],'] [', time.localtime(newEvent['startTime']),']'
            while newEvent['startTime'] <= endTime and newEvent['startTime'] <= newEvent['repeatEvent']['endDate']:
                #print 'Adding [', newEvent['text'], '] [', time.localtime(newEvent['startTime']), ']'
                retVal.append(newEvent.copy())
                newEvent = getNextRepeatedEvent(newEvent)
    return retVal

def getNextRepeatedEvent(event):
    import time
    '''A sample from datebookList:
    'repeatEvent': {'brand': 5L,        Daily, Weekly, Monthly Date, Monthly Day, YEARLY
        'brandDayNumber': 4L,        4th
        'brandMonthIndex': 7L,        August
        'dateExceptionCount': 0,
        'endDate': 1028437200L,
        'firstDayOfWeek': 0L,
        'interval': 1L,
        'repeatEventFlag': 65535},
    '''
    repeatDetails = event['repeatEvent']
    repeatStartDST = time.localtime(event['startTime'])[8]
    if repeatDetails['brand'] == 1:    #daily repeat
        event['startTime'] = event['startTime'] + 60*60*24*repeatDetails['interval']
    elif repeatDetails['brand'] == 2:    # repeat weekly on specific days
        targetDaysMask = ord(repeatDetails['brandDaysMask']) #convert character read from file to ascii code
        #print 'targetDaysMask:', targetDaysMask
        repeatStartLocal=time.localtime(event['startTime'])
        if repeatStartLocal[6] == 5: # event's current start time is a Saturday
            '''add one day to get to Sunday, then add whole weeks
            according to the specified interval minus one, because we
            just went from Saturday to Sunday with the first addition.
            '''
            event['startTime'] = event['startTime'] + (60*60*24) + (60*60*24*7) * (repeatDetails['interval'] - 1)    
            repeatStartLocal=time.localtime(event['startTime'])
        else:
            event['startTime'] = event['startTime'] + (60*60*24)
            repeatStartLocal=time.localtime(event['startTime'])
        
        '''Python stores Wdays in element 6 of a time_struct,
        but stores them with Monday as 0 and Sun as 6.
        This line converts from the python time_struct to a WDay value with Sunday as 0
        '''
        rsWDay = (repeatStartLocal[6] + 1) % 7
        #print time.localtime(event['startTime']),'\n\trsWDay:', rsWDay,'\n\t', 2**rsWDay,'\n\t', not ((2**rsWDay) & targetDaysMask)
        while not ((2**rsWDay) & targetDaysMask): # targetDaysMask is sum of the following: 1 = Sunday, 2 = Monday, 4 = Tues, . . . , 64 = Saturday
            event['startTime'] = event['startTime'] + (60*60*24)
            repeatStartLocal=time.localtime(event['startTime'])
            rsWDay = (repeatStartLocal[6] + 1) % 7
    elif repeatDetails['brand'] == 3:    #repeat monthly based on day
        from calendar import monthrange
        targetDay = repeatDetails['brandDayIndex'] #returns wday according to Python standards with Monday = 0
        targetWeek = repeatDetails['brandWeekIndex'] #returns week with first week = 0, fourth week = 3, and last week = 4
        for interval in range(1, repeatDetails['interval'] + 1):
            if targetWeek == 4: #event repeats on last ?day of the month.
                #event['startTime'] = event['startTime'] + (60*60*24*7) #add one week to current event
                newTime = event['startTime'] + (60*60*24*7*4) #add four weeks to current event
                newLocalTime = time.localtime(newTime)
                monthBegins, monthLength = monthrange(newLocalTime[0], newLocalTime[1])
                if (monthLength - newLocalTime[3]) >= 7: newTime = newTime + (60*60*24*7)
                event['startTime'] = newTime
            else: #repeats on 1st - 4th ?day of month
                newTime = event['startTime']
                newLocalTime = time.localtime(newTime)
                oldStartTimeMonth = newLocalTime[1]
                #advance event until it's the first occurrence of that weekday in the next month
                while newLocalTime[1] == oldStartTimeMonth:
                    newTime = newTime + (60*60*24*7) #add one week to current event
                    newLocalTime = time.localtime(newTime)
                event['startTime'] = newTime + (60*60*24*7*(targetWeek))
    elif repeatDetails['brand'] == 4:
        #repeat monthly based on date
        repeatStartLocal = time.localtime(event['startTime'])
        event['startTime'] = time.mktime((repeatStartLocal[0], repeatStartLocal[1]+repeatDetails['interval'], repeatStartLocal[2], repeatStartLocal[3], repeatStartLocal[4], repeatStartLocal[5], 0, 0, 0))
    elif repeatDetails['brand'] == 5:
        #repeat yearly based on date
        repeatStartLocal = time.localtime(event['startTime'])
        event['startTime'] = time.mktime((repeatStartLocal[0]+repeatDetails['interval'], repeatStartLocal[1], repeatStartLocal[2], repeatStartLocal[3], repeatStartLocal[4], repeatStartLocal[5], 0, 0, 0))
    
    newEventDST = time.localtime(event['startTime'])[8]
    correctDST = repeatStartDST - newEventDST
    event['startTime'] = event['startTime'] + (60*60*correctDST)
    return event

def getAppointment(event):
    return event

def createAppointment(event):
    return event

def changeAppointment(event):
    return


if __name__ == "__main__":
    import sys
    import getopt
    try:
        options, args = getopt.getopt(sys.argv[1:], 'v')
        fileToRead = args[0]
        verbose = len(options) > 0 and options[0][0] == "-v"
    except:
        print "Usage: python palmFile.py [-v] <fileName>"
        print "-v for verbose, print all the data in the file"
        print "Prints out some sample data from a palm file"
        exit(-1)
    palmData = readPalmFile(fileToRead)
    if verbose:    
        import pprint
        pprint.pprint(palmData)
    if palmData[0]["versionTag"] == 1094844672L: # addresses
        printAllNames(palmData)
    elif palmData[0]["versionTag"] == 1145176320L: # datebook
        printAWeekWorthOfCalendar(palmData)
