'''
http://phonebook.fm.intel.com/cgi-bin/phonebook?e=^11298587$&f=ALL&d=WWID&x=0&z=y&p=y&c=-DomainAddress
http://phonebook.fm.intel.com/cgi-bin/phonebook?e=^jwojcik$&f=ALL&d=IDSID&x=0&z=y&p=y&c=WWID&c=IDSID&c=MgrWWID&c=MgrName&c=-DomainAddress&c=BookName&c=EmpType

'''
import re
import os.path
import json
import requests
import argparse

def get_email_by_wwid(wwid):
    phone_url = 'http://phonebook.fm.intel.com/cgi-bin/phonebook?e=^' + wwid + '$&f=ALL&d=WWID&x=0&z=y&p=y&c=-DomainAddress'
    wwid_email = requests.get(phone_url).text.split('\n')[1].split('|')[0]
    return wwid_email

def get_recipient_data_by_idsid(idsid):
    user_data = dict()
    phone_url = 'http://phonebook.fm.intel.com/cgi-bin/phonebook?e=^' + idsid + '$&f=ALL&d=IDSID&x=0&z=y&p=y&c=IDSID&c=WWID&c=MgrWWID&c=EmpType&c=-DomainAddress&c=BookName'
    idsid_data = requests.get(phone_url).text.split('\n')[1].split('|')
    user_data.update({'wwid':idsid_data[1]})
    user_data.update({'EmpType':idsid_data[3].strip()})
    user_data.update({'name':idsid_data[5]})
    user_data.update({'first_name':idsid_data[5].split(', ')[1]})
    user_data.update({'email':idsid_data[4]})
    user_data.update({'mgr_email':get_email_by_wwid(idsid_data[2])})
    return user_data

def get_recipient_dict(idsid_set):
    recipient_dict = dict()
    for idsid in idsid_set:
        if bool(re.search('^(?!sys_).*', idsid)) and idsid:
            recipient_dict.update({idsid:get_recipient_data_by_idsid(idsid)})
    return recipient_dict

def save_error(error_file_name, error_msg):
    print(error_msg)
    with open(error_file_name, 'w+') as error_file:
        error_file.write(error_msg)

def main(data_file, hsdes_recipient_field, recipient_file='recipient_dict.json'):
    exit_code = 1
    with open(data_file, 'r') as results_file:
        results = json.loads(results_file.read())
    if int(results['total']) > 0:
        if hsdes_recipient_field in results['data'][0].keys():
            recipient_set = set()
            for bug in results['data']:
                recipient_set.add(bug[hsdes_recipient_field])
            with open(recipient_file, 'w+') as recipient_dict_file:
                json.dump(get_recipient_dict(recipient_set), recipient_dict_file)
            exit_code = 0
        else:
            save_error('hsdes_field_error.txt', 'no ' + hsdes_recipient_field + ' field in the query')
    else:
        save_error('hsdes_query_error.txt', 'no query data')
    return exit_code

if __name__ == '__main__':
    print(os.path.abspath(os.getcwd()))
    print(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument('-d', help='hsdes data file default=hsdes_query_data.json ', required=False, default='hsdes_query_data.json')
    ap.add_argument('-f', help='hsdes recipient field name default=owner', required=False, default='owner')
    ap.add_argument('-o', help='recipient dict file default=recipient_dict.json ', required=False, default='recipient_dict.json')
    parsed = ap.parse_args()
    EXIT_CODE = main(parsed.d, parsed.f, parsed.o)
    exit(EXIT_CODE)