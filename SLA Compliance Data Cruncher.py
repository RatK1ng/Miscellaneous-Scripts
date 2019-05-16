print('Setting up modules and variables')
import pandas as pd
from math import floor, ceil
from datetime import datetime, timedelta
import dateutil
from dateutil.rrule import *
#import numpy as np
import re
import copy

# Length of month
rawintervals = []
currentevents = []
logname = ''
# Essentially a merged events array, holding arrays shaped like [start time, end time, severity], this list should have a
tvlist = ['TV 43', 'TV 44', 'TVs 45 to 54', 'TV56 & 57', 'TV 58 to 77', 'TV 42 to 44']

# Sets up 2D Dictionary holding values for each relevant severity levels' maximum downtime a month in minutes.
# The number is calculated by dividing the weekly allowable downtime by 7, and multiplying it by the length of the month
# Han has said the base number is incorrect due to SLA being vague, but the arithmetic applied is correct
# First number in the "floor(...)" is the total number of equipment of that category



zonestatus = [0 for x in range(1, 3)]
# 2D list holding the current status of the Zone (i.e zone x is at severity 2), used at the end of each minutley loop


problemclasses = {1: {}, 2: {}, 3: {}, 4: {}, 5: {},
                  6: {}, 7: {}, 8: {}, 9: {}, 10: {}, 11: {}, 12: {}}
# Problemclasses holds count or number of problems at the current time 'dt', is used for calculating relevant severity levels

def statuschange(zone, severitylevel):
    checkcompleted = True
    if zonestatus[zone] > severitylevel or zonestatus[zone] == 0:
        zonestatus[zone] = severitylevel
# This function increases the severity level in the relevant zone, depending on it's already existing severity, as it can only be overriden by a more severe warning level
# I.E A rule might incur the Zone 4

#slasample.csv
'''-----------------BEGIN SETUP FOR DATAFRAMES-----------------------'''
while not re.search(r'^.*\.csv$', logname):
    logname = input('Please enter the filename for the logs\n')
print('Setting up Dataframes')
sampledata = pd.read_csv(
    logname, encoding="ISO-8859-1", sep=',')  # Have to import with better encoding
# Reads file csv containing logs with a header
# Date,Area,Plant Item,OOS Time,RTS Time,Duration minutes Today,Fault Description,Downtime Excluded,Reason for Exclusion,Zone, Severity
assetlist = pd.read_csv("assetlistpython.csv", encoding="ISO-8859-1", sep=',')
# Dataseries setup from an export from Maximo from the asset list of IAG Cargo, this can be used in finding out what areas to assign the less specific naming convetions of RC
# Asset,Description,Location,Failure Class,Parent,Primary Customer,Rotating Item,Status,Site

#print(sampledata
sampledata['Severity'] = ''
sampledata['RTS Time'].fillna('TBF', inplace=True)
sampledata['Date'].fillna('Error', inplace=True)
# NaN values in RTS Time column are replaced with ToBeConfirmed where issues are not yet resolved

temp = sampledata['Plant Item'] == ('TV43' or 'TV 43')
sampledata.loc[temp, 'Area'] = 'TV 43'
temp = sampledata['Plant Item'] == ('TV44' or 'TV 44')
sampledata.loc[temp, 'Area'] = 'TV 44'

temp = sampledata['Plant Item'].str.match(r'\bMCC[0-9]([0-9] | )FG[0-9]{2} Deck( [0-9]+|[0-9]+)', case=False, flags=0)
temp.fillna(False, inplace=True)
sampledata.loc[temp, 'Area'] = 'Roller Decks'

temp = sampledata['Plant Item'].str.match(r'\bETI', case=False, flags=0)
temp.fillna(False, inplace=True)
sampledata.loc[temp, 'Area'] = 'ETI'

temp = sampledata['Plant Item'].str.match(r'\bCastor', case=False, flags=0)
temp.fillna(False, inplace=True)
sampledata.loc[temp, 'Area'] = 'Castor Deck'
# Various rules to allocate my own "custom" areas based on a regular expression match in the "Plant Item" field of the data series
# This is done for the purposes of categorization in the main Rule Loop

temp = sampledata['Area'].isin(['MCC 1 to 3', 'MCC 4 to 11'])
# pandas series made from the rows that have area of MCC
for x in sampledata[temp].index:
    match = re.search(r'MCC([0-9]{1,2}) \D+([0-9]{1,2}) \D+([0-9]{1,2})', sampledata[temp].at[x, 'Plant Item'], re.IGNORECASE)
    if match:
        groups = match.group(1, 2, 3)
        matches = list(groups)
        for i in range(1, 3):
            if len(matches[i]) < 2:
                matches[i] = '0' + matches[i]
                # If someone only typed DK1 instead of DK01 this fixes it        
        newstring = ' '.join(('MCC' + matches[0], 'FG' + matches[1], 'DK' + matches[2]))
        regsearch = str('    (.*) - ' + newstring)
        matchedasset = assetlist['Description'].str.contains(newstring, regex=True)
        matchedasset = assetlist[matchedasset]['Description'].to_string()
        # Creates a string of the description of the matching assets
        whatis = re.search(regsearch, matchedasset)    
        if whatis == 'RIGHT ANGLE DECK':
            sampledata.at[i, 'Area'] = 'RA Deck'
        elif re.search(r'TURNTABLE', matchedasset):
            sampledata.at[i, 'Area'] = 'Turntable'

'''-----------------------------END SETUP FOR DATAFRAMES---------------------------------------------------'''



'''-----------------------------BEGIN RULE FOR STORAGE TRANSFER VEHICLES AKA STVS--------------------------'''
print('Configuring STVs')
sampledata['Plant Item'].replace(to_replace=(
    'STV ', 'STV'), value='STORAGE TRANSFER VEHICLE ', regex=True, inplace=True)
# Makes STV xxx appear as STVxxx so that logs are consistent with naming protocols

stv_values = ((sampledata['Plant Item'])[sampledata['Plant Item'].str.contains(
    'STORAGE TRANSFER VEHICLE', na=False)]).values
stv_index = (sampledata.index[sampledata['Plant Item'].str.contains(
    'STORAGE TRANSFER VEHICLE', na=False)]).values
stv_lookup = [list(t) for t in zip(stv_values, stv_index)]
del stv_values, stv_index
# Create lookup 2D Tuple for STVs, holding [[STV ID, index of related log],[etc]]

# sampledata.at[2,'Zone'] = 420
# Example of per cell data replacement


for i in range(len(stv_lookup)):
    temp = ((assetlist['Location'])[
            assetlist['Description'].str.contains(stv_lookup[i][0], na=False)]).values

    # sampledata.at[(stv_lookup[i][1]), 'Zone'] = (str(temp[0])[0:2])
    rawintervals.append(sampledata.iloc[(stv_lookup[i][1])][[
                        'Date', 'OOS Time', 'RTS Time']].tolist())

    rawintervals[i].append(stv_lookup[i][1])
# Looks up the STV IDs from stv_lookup in the asset list, pulls the location, and returns the zone ID part of the location into the sampledata dataframe

# print(str(list(stv_lookup)))
(sampledata['Plant Item'])[
    sampledata['Plant Item'].str.contains('STV', na=False)]
'''-----------------END RULE FOR STORAGE TRANSFER VEHICLES AKA STVS-----------------------------------------'''


print('Begining time setup')
temp =''
while not re.search(r'\b[0-9]{4}\/[0-9][0-2]?\/[0-3]?[0-9]\b',str(temp)):
    temp = input('Enter start date for data process in format YYYY/MM/DD\n')
#starttime = datetime(2019, 1, 1)
temp = temp.split('/')
starttime = datetime(int(temp[0]), int(temp[1]), int(temp[2]))
temp = ''

while not re.search(r'\b[0-9]{4}\/[0-9][0-2]?\/[0-3]?[0-9]\b',str(temp)):
    temp = input('Enter end date for data process in format YYYY/MM/DD\n')
temp = temp.split('/')
endtime = datetime(int(temp[0]), int(temp[1]), int(temp[2]))
# SetUp the upper and lower limit of dates from which the loop iterates through
# In the format (year, month, day)
allintervals = sampledata[['Date', 'OOS Time', 'RTS Time']].values
# Lookup list holdng the dates of problems and their start/end time, note it is indexed in the same
# Order as the pandas datastructure thus allowing it to be used to lookup logs
monthlength = (endtime - starttime).days
zoneminutes = {'zone 1': {'Severity 1': floor(55 * 100 / 7 * monthlength), 'Severity 2': floor(84 * 302 / 7 * monthlength), 'Severity 3': floor(11 * 504 / 7 * monthlength), 'Severity 4': floor(14 * 1000 / 7 * monthlength), },
               'zone 2': {'Severity 1': floor(16 * 100 / 7 * monthlength), 'Severity 2': floor(96 * 302 / 7 * monthlength), 'Severity 3': floor(1 * 504 / 7 * monthlength), 'Severity 4': floor(16 * 1000 / 7 * monthlength), },
               'zone 3': {'Severity 1': floor(78 * 100 / 7 * monthlength), 'Severity 2': floor(26 * 302 / 7 * monthlength), 'Severity 3': floor(30 * 504 / 7 * monthlength)},
               'zone 4': {'Severity 1': floor(531 * 100 / 7 * monthlength), 'Severity 2': floor(531 * 302 / 7 * monthlength), 'Severity 3': floor(407 * 504 / 7 * monthlength), 'Severity 4': floor(10566 * 1000 / 7 * monthlength), },
               'zone 5': {'Severity 1': floor(58 * 100 / 7 * monthlength), 'Severity 2': floor(58 * 302 / 7 * monthlength), 'Severity 3': floor(123 * 504 / 7 * monthlength), 'Severity 4': floor(36 * 1000 / 7 * monthlength), },
               'zone 6': {'Severity 1': floor(312 * 100 / 7 * monthlength), 'Severity 2': floor(316 * 302 / 7 * monthlength), 'Severity 3': floor(126 * 504 / 7 * monthlength), 'Severity 4': floor(50 * 1000 / 7 * monthlength), },
               'zone 7': {'Severity 1': floor(15 * 100 / 7 * monthlength), 'Severity 2': floor(15 * 302 / 7 * monthlength)},
               'zone 8': {'Severity 1': floor(154 * 100 / 7 * monthlength), 'Severity 2': floor(106 * 302 / 7 * monthlength), 'Severity 3': floor(65 * 504 / 7 * monthlength)},
               'zone 9': {'Severity 1': floor(44 * 100 / 7 * monthlength), 'Severity 2': floor(23 * 302 / 7 * monthlength), 'Severity 3': floor(2 * 504 / 7 * monthlength)},
               'zone 10': {'Severity 1': floor(5 * 100 / 7 * monthlength), 'Severity 2': floor(4 * 302 / 7 * monthlength)},
               'zone 11': {'Severity 1': floor(100 / 7 * monthlength), 'Severity 2': floor(302 / 7 * monthlength)},
               'zone 12': {'Severity 1': floor(100 / 7 * monthlength), 'Severity 2': floor(302 / 7 * monthlength)}}

# Static copy of zoneminutes so that the minutes used by zones can be calculated via comparing the values in zoneminute
zonecompare = copy.deepcopy(zoneminutes)
# with the values in zonecompare


for dt in rrule(MINUTELY, dtstart=starttime, until=endtime):
    # Minute by minute loop
    for i in range(len(allintervals)):
        if allintervals[i][0] == 'Error':
            break
        if not isinstance(allintervals[i][1], str) :
            allintervals[i][1] = '00:00:00'
        # Ignores the current entry if there is incorrect date
    
        begin = datetime.strptime(' '.join(
            (str(allintervals[i][0]), str(allintervals[i][1]))), '%d/%m/%Y %H:%M:%S')
        if allintervals[i][2] == 'TBF':
            end = (datetime.strptime(
                allintervals[i][0], '%d/%m/%Y')) + timedelta(days=1)
        else:
            end = datetime.strptime(
                (' '.join((allintervals[i][0], allintervals[i][2]))), '%d/%m/%Y %H:%M:%S')
        # Setups the begin and end datetime values

        if dt >= begin and dt < end:
            currentevents.append(i)
        # Checks if the event contained in allintervals[i] falls in the current time

    '''------------------ BEGIN ZONING/SEVERITY RULES ------------------------'''
    for i in range(len(currentevents)):
        if sampledata.iloc[currentevents[i]]['Duration minutes Today'] == sampledata.iloc[currentevents[i]]['Downtime Excluded']:
            break
        # If the curent event running at the current time (dt) has the same downtime duration as the downtime exlcuded, then stop processing it
        else:
            try:
                problemclasses[sampledata.iloc[currentevents[i]]
                               ['Zone']][sampledata.iloc[currentevents[i]]['Area']] += 1
            except KeyError:
                problemclasses[(sampledata.iloc[currentevents[i]]['Zone'])][(
                    sampledata.iloc[currentevents[i]]['Area'])] = 1
            # Iterating a problemclasses count field for when multiple instances exist simultaneously
            # Creates a new problemclass entry for when a problem name doesn't exist

    # Increment counters in the problemclasses dictionary

    msg = re.findall(
        r"\'[A-z 0-9\"]+\'|\"[A-z 0-9\']+\"", str(problemclasses))
    print(', '.join(msg), dt)
    # Formatting the minutley message with the probems and datetime stamp
    if msg != []:
        print('theres something there')
        if 'RA Deck' in problemclasses[1]:
            statuschange(1, 1)
        if 'RA Deck' in problemclasses[2]:
            statuschange(2, 2)
        if 'RA Deck' in problemclasses[3]:
            if problemclasses[3]['RA Deck'] == 1:
                statuschange(3, 2)
            elif problemclasses[3]['RA Deck'] > 1:
                statuschange(3, 1)
        if 'RA Deck' in problemclasses[4]:
            if problemclasses[4]['RA Deck'] == 1:
                statuschange(4, 3)
            elif problemclasses[4]['RA Deck'] == 2:
                statuschange(4, 2)
            elif problemclasses[4]['RA Deck'] > 2:
                statuschange(4, 1)
        if 'RA Deck' in problemclasses[5]:
            statuschange(5, 3)
        if 'RA Deck' in problemclasses[6]:
            if problemclasses[6]['RA Deck'] > 1:
                statuschange(6, 1)
            elif problemclasses[6]['RA Deck'] == 1:
                statuschange(6, 2)
        if 'RA Deck' in problemclasses[8]:
            if problemclasses[8]['RA Deck'] == 1:
                statuschange(8, 2)
            if problemclasses[8]['RA Deck'] > 1:
                statuschange(8, 1)
            if 'RA Deck' in problemclasses[9]:
                if problemclasses[9]['RA Deck'] == 1:
                    statuschange(9, 2)
                if problemclasses[9]['RA Deck'] > 1:
                    statuschange(9, 1)    
        if 'RA Deck' in problemclasses[10]:
            statuschange(10, 1)
        # RA Deck rules
        
        if 'Turntable' in problemclasses[3]:
            statuschange(3, 1)
        if 'Turntable' in problemclasses[6]:
            if problemclasses[6]['Turntable'] > 1:
                statuschange(6, 1)
            elif problemclasses[6]['Turntable'] == 1:
                statuschange(6, 2)    
        if 'Turntable' in problemclasses[8]:
            if problemclasses[8]['Turntable'] == 1:
                statuschange(8, 2)
            elif problemclasses[8]['Turntable'] > 1:
                statuschange(8, 1)
        if 'Turntable' in problemclasses[9]:
            statuschange(9, 1)
        # Turntables 
        
        if 'TV 42 to 44' in problemclasses[1]:
            statuschange(1, 2)
        if 'TV 43' in problemclasses[2]:
            statuschange(2, 2)
        if 'TV 44' in problemclasses[2]:
            statuschange(2, 1)
        # TVs for zone 1 & 2
    
        if 'Castor Deck' in problemclasses[10]:
            if problemclasses[10]['Castor Deck'] in range(5, 9):
                statuschange(10, 2)
            elif problemclasses[10]['Castor Deck'] > 9:
                statuschange(10, 1)
        if 'Castor Deck' in problemclasses[9]:
            statuschange(9, 3)
    
        if 'ETI' in problemclasses[1]:
            statuschange(1, 2)
        if 'MTD' in problemclasses[1]:
            statuschange(1, 1)
        if 'ETI' in problemclasses[2]:
            statuschange(1, 2)
        if 'MTD' in problemclasses[2]:
            statuschange(1, 1)
        if 'MTD' in problemclasses[8]:
            statuschange(8, 1)
        if 'MTD' in problemclasses[10]:
            if problemclasses[10]['MTD'] == 1:
                statuschange(10, 2)
            elif problemclasses[10]['MTD'] > 1:
                statuschange(10, 1)
        # MTDs and ETIs in various zones
    
        if "STV's" in problemclasses[4]:
            if (problemclasses[4]["STV's"]) > 2:
                statuschange(4, 1)
            elif problemclasses[4]["STV's"] == 1:
                statuschange(4, 2)
        # STVs in Zone 4
    
        if 'Manip' in problemclasses[6]:
            if problemclasses[6]['Manip'] == 1:
                statuschange(6, 3)
            if problemclasses[6]['Manip'] == 2:
                statuschange(6, 2)
            if problemclasses[6]['Manip'] > 2:
                statuschange(6, 1)
        # Manipulators in Zone 6
    
        for key in problemclasses[4]:
            if re.match(r'\bTV', key):
                temp = problemclasses[4][key]
                if temp == 1:
                    statuschange(4, 2)
                elif temp > 1:
                    statuschange(4, 1)
        # TVs in Zone 4 (less of a botch)
    
        temp = 0
        for key in problemclasses[6]:
            if re.match(r'\bTV', key):
                temp = problemclasses[6][key]
                if temp == 1:
                    statuschange(6, 3)
                elif temp == 2:
                    statuschange(6, 2)
                elif temp > 2:
                    statuschange(6, 1)
        # TVs in Zone 6
    
        temp = 0
        if 'Roller Decks' in problemclasses[1]:
            statuschange(1, 2)
        if 'Roller Decks' in problemclasses[2]:
            statuschange(2, 2)
    
    
        if 'BTVs' in problemclasses[5]:
            if problemclasses[5]['BTVs'] == 1:
                statuschange(5, 2)
            elif problemclasses[5]['BTVs'] > 1:
                statuschange(5, 1)
        if 'DTVs' in problemclasses[5]:
            if problemclasses[5]['DTVs'] == 1:
                statuschange(5, 2)
            elif problemclasses[5]['DTVs'] > 1:
                statuschange(5, 1)
        # BTV ad DTVs in Zone 5
    
        if 'MTD' in problemclasses[1]:
            statuschange(1, 1)
        temp = 0
        if 'MCC 1 to 3' in problemclasses[1]:
            statuschange(1, 1)
        if 'MCC 1 to 3' in problemclasses[2]:
            statuschange(1, 2)
        if 'MCC 1 to 3' in problemclasses[4]:
            temp += problemclasses['MCC 1 to 3']
        if 'MCC 4 to 11' in problemclasses[4]:
            temp += problemclasses['MCC 4 to 11']
        if temp == 1:
            statuschange(4, 2)
        elif temp > 1:
            statuschange(4, 1)
        if ('MCC 1 to 3' or 'MCC 4 to 11') in problemclasses[6]:
            statuschange(6, 1)
        temp = 0
        if 'MCC 1 to 3' in problemclasses[8]:
            statuschange(8, 1)
        if 'MCC 1 to 3' in problemclasses[9]:
            statuschange(9, 1)
        # MCC Hoists
    
        if 'Cage Hoists' in problemclasses[4]:
            if problemclasses[4]['Cage Hoists'] == 1:
                statuschange(4, 2)
            if problemclasses[4]['Cage Hoists'] > 1 and zonestatus[4] > 1:
                statuschange(4, 1)
        if 'Cage Hoists' in problemclasses[5]:
            if problemclasses[5]['Cage Hoists'] == 2:
                statuschange(5, 2)
            if problemclasses[5]['Cage Hoist'] > 2:
                statuschange(5, 1)
        if 'Cage Hoists' in problemclasses[6] and zonestatus[6] > 1:
            zonestatus[6] = 1
        if 'Cage Hoists' in problemclasses[7]:
            if problemclasses[7]['Cage Hoists'] == 1:
                statuschange(7, 2)
            elif problemclasses[7]['Cage Hoists'] > 1:
                statuschange(7, 1)
        if 'Cage Hoists' in problemclasses[8]:
            if problemclasses[8]['Cage Hoists'] > 0:
                statuschange(8, 1)
        # Cage Hoists in all areas
    
        if 'Chillers' in problemclasses[1]:
            if problemclasses[1]['Chillers'] in range(4, 6):
                statuschange(1, 3)
            elif problemclasses[1]['Chillers'] in range(6, 8):
                statuschange(1, 2)
            elif problemclasses[1]['Chillers'] > 7:
                statuschange(1, 1)
        # Chillers, should be perfect
    
        if 'DTVs' in problemclasses[5]:
            if problemclasses[5]['DTVs'] == 1:
                statuschange(5, 2)
            if problemclasses[5]['DTVs'] > 1:
                statuschange(5, 1)
        if 'BTVs' in problemclasses[5]:
            if problemclasses[5]['BTVs'] == 1:
                statuschange(5, 2)
            if problemclasses[5]['BTVs'] > 1:
                statuschange(5, 1)
        # DTVs and BTVs, should be perfect
    
        if 'Dolly Dock & Uni Docks' in problemclasses[3]:
            if problemclasses[3]['Dolly Dock & Uni Docks'] == 1:
                statuschange(3, 2)
            if problemclasses[3]['Dolly Dock & Uni Docks'] > 1:
                statuschange(3, 1)
        if 'Dolly Dock & Uni Docks' in problemclasses[8]:
            if problemclasses[8] == 1:
                statuschange(8, 2)
            if problemclasses[8] > 1:
                statuschange(8, 1)
    else:
        print('That was empty')
        # Dolly Docks & Uni Docks, should be perfect (might need more rules but these two are perfect)
        # In each of these blocks of rules, they call the statuschange function which changes the severity of the zone if the conditions are met (e.g 9 chillers are OOS)
        
    ''' - ----------------- END ZONING / SEVERITY RULES - -------------------------'''
    for x in range(1, len(zonestatus)):
        if zonestatus[x] != 0:
            zoneminutes['zone ' +
                        str(x)]['Severity ' + str(zonestatus[x])] -= 1

    # Removes a minute from the pool each zone has for permitted downtime according to zonestatus

    problemclasses = {1: {}, 2: {}, 3: {}, 4: {}, 5: {},
                      6: {}, 7: {}, 8: {}, 9: {}, 10: {}, 11: {}, 12: {}}
    del currentevents[:]
    zonestatus = [0 for x in range(1, 13)]
    # Resets various variables used in the loops to keep track of problems, and current status as it all needs to be recalculated in the next minute

print('\n')
for x in range(1, 13):
    for y in range(1, 5):
        if ('Severity ' + str(y)) in zoneminutes['zone ' + str(x)]:
            if zonecompare['zone ' + str(x)]['Severity ' + str(y)] != zoneminutes['zone ' + str(x)]['Severity ' + str(y)]:
                diff = zonecompare['zone ' + str(x)]['Severity ' + str(
                    y)] - zoneminutes['zone ' + str(x)]['Severity ' + str(y)]
                newdate = starttime.replace(month=starttime.month + 1, day=1)
                predict = (newdate - endtime).days
                currentpercent = round((diff / zonecompare['zone ' + str(x)]['Severity ' + str(y)] * 100), 2)
                futurepercent = ceil(diff / zonecompare['zone ' + str(x)]['Severity ' + str(y)] * 100 / (endtime.day - starttime.day) * (newdate - timedelta(days=1)).day)
                # Predicts the usage for the zone severity, using a linear model (how much has been used so far /time elapsed * time left in 
                print('Zone', x, 'severity', y, 'used', diff, 'minutes, out of an avalible', zonecompare['zone ' + str(x)]['Severity ' + str(y)], ','
                      'Usage for the month so far:', str(currentpercent))
# Display the zone/severities' where time has been used
# Only displays it when a change has been made (if a zone is on severity 0 i.e never had a problem) no output will be displayed


'''----------------------------BEGIN OUTPUTTING DATA TO CSV FILE---------------------------------'''

filename = input('Write filename for exporting...\n')+'.csv'
datatowrite = ''
with open(filename, 'w') as file:
    for zone in zoneminutes:
        for severity in zoneminutes[zone]:
            currentdata = (zone + ' ' + severity).replace('zone ', 'Z')
            datatowrite += (currentdata+'\t')
            pass
    datatowrite+='\n'    
    for zone in zoneminutes:
        for severity in zoneminutes[zone]:
            datatowrite += (str(zonecompare[zone][severity] - zoneminutes[zone][severity])+'\t')
        pass
    datatowrite+='\n'
    for zone in zoneminutes:
        for severity in zoneminutes[zone]:
            datatowrite += (str(zonecompare[zone][severity])+'\t')
        pass
    datatowrite+='\n'
    for zone in zoneminutes:
        for severity in zoneminutes[zone]:
            datatowrite+= str(100 - round(( (zonecompare[zone][severity] - zoneminutes[zone][severity]) / zonecompare[zone][severity] * 100), 2)) +'%'+'\t'
            pass
    datatowrite = datatowrite.replace('Severity ', 'S')
    #print(datatowrite)
    file.write(datatowrite)
'''----------------------------END OUTPUTTING DATA TO CSV FILE------------------------------------'''

input('Press any key to exit...\n')
