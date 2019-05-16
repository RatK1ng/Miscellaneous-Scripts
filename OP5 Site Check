import requests
import re
import json
import warnings
import string

ip = input('Please enter your target ip')
alertpage = 'https://' + ip + '/api/'
command = 'filter/query?format=json'
query = '&query=[services] state !=0 and acknowledged = 0 and ' \
        'scheduled_downtime_depth = 0 and host.scheduled_downtime_depth = 0'
authentication = ['username', 'password']
warnings.filterwarnings("ignore")


def queryconstructor():
    global addr
    alertpage = 'https://' + ip + '/api/'
    if 'query' not in command:
        addr = (alertpage + command)
    else:
        addr = (alertpage + command + query)


def translatejson():
    datafile = open('Data.json', 'r')
    data = datafile.read()
    data = data.replace("\'", "\"")
    data = re.sub(r'with command name "([a-z]*)""', 'with command name \\1\"', data)
    data = re.sub(r'("Check_number_of_FS_MCS".*string: )(")(")', r'\1\\\2\\\3', data)
    datafile.close
    datafile = open('Data.json', 'w')
    datafile.write(data)
    datafile.close()


def readalerts():
    translatejson()
    with open('Data.json') as j:
        jsondata = json.loads(j.read())
        # newjsondata = [x for x in jsondata if x['type'] == '1']
        problemcount = 0
        print('-' * 30 + '\n')
        for x in range(0, len(jsondata["services_with_info"])):
            #if jsondata["services_with_info"][x][1] != 0:
            print('Error name:', jsondata["services_with_info"][x][0] + ':')
            print(jsondata["services_with_info"][x][3] + '\n')
            problemcount += 1
        print(hosts[e], 'has', problemcount, 'errors\n\n')


def querytofile():
    global data
    queryconstructor()
    result = requests.get(addr, auth=(authentication[0], authentication[1]), verify=False)
    data = result.json()
    datafile = open('Data.json', 'w+')
    datafile.write(str(data))
    datafile.close()


'''
START OF PROGRAM
'''

querytofile()
with open('Data.json') as j:
    data = j.read()
data2write = (str(data).replace("{'host':", "\n{'host':")).replace('\n', '', 1).replace("'", '"').replace('True',
                                                                                                          '"TRUE"').replace(
    'False', '"FALSE"')
datafile = open('Data.json', 'w+')
datafile.write(str(data2write))
print('Finished exporting to file')

with open('Data.json') as j:
    hosts = re.compile(r'"name": "(.*)", "next_check"').findall(j.read())
    print(list(set(hosts)))

for e in range(len(hosts)):
    command = ('status/host/' + hosts[e] + '?format=json')
    if 'vir' in str(hosts[e]):
        print('Perform the health check on machine\"', hosts[e], '\" manually, as the alerts are written by a fool')
    else:
        print(hosts[e])
        querytofile()
        readalerts()
