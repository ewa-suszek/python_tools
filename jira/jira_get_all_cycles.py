'''
https://jira.devtools.intel.com/rest/zapi/latest/cycle?projectId=38300&versionId=&id=&offset=&issueId=&expand=

'''

import re
import os
import sys
import json
import base64
import requests
from getpass import getpass
from requests_kerberos import HTTPKerberosAuth
import urllib3
urllib3.disable_warnings()



def main(argv):
    global my_hashed_password

    my_hashed_password = read_password()
    get_all_cycles()

def read_password():
    try:
        pass_file = open(os.path.join(os.environ['USERPROFILE'], '.python_jira'), "rb+")
        hashed_pass = pass_file.read()
    except:
        password = getpass()
        hashed_pass = base64.b64encode(str.encode(password))
        pass_file = open(os.path.join(os.environ['USERPROFILE'], '.python_jira'), "ab+")
        pass_file.write(hashed_pass)
    pass_file.close()
    return hashed_pass

def get_user_name_and_pass(your_hashed_pass):
    return os.environ['USERNAME'], base64.b64decode(your_hashed_pass).decode('utf-8')

def search_dictionary(dictionary,param):
    return_list = []
    if param in dictionary:
        #print(dictionary[param])
        return_list.append(dictionary[param]) 
    for key in dictionary:
        value = dictionary[key]
        if isinstance(value,dict):
            return_list.extend(search_dictionary(value,param))
        if isinstance(value,list):
            return_list.extend(search_list(value,param))
    return return_list


def search_list(my_list,param):
    return_list = []
    for value in my_list:
        if isinstance(value,dict):
            return_list.extend(search_dictionary(value,param))
        if isinstance(value,list):
            return_list.extend(search_list(value,param))
    return return_list

def get_all_cycles():
    cycles_list = list()
    result = '-----'
    headers = { 'Content-type': 'application/json' }
    url = 'https://jira.devtools.intel.com/rest/zapi/latest/cycle?projectId=38300&versionId=&id=&offset=&issueId=&expand='
    response = requests.get(url, verify=False, auth=requests.auth.HTTPBasicAuth(get_user_name_and_pass(my_hashed_password)[0],get_user_name_and_pass(my_hashed_password)[1]), headers = headers,  proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    try:
        cycles = response.json()
        cycles_list = search_dictionary(cycles,'name')    
    except:
        pass

    for cycle in cycles_list:
        print(f'[{cycle}]')
    return result


if __name__ == '__main__':
    main(sys.argv[1:])
