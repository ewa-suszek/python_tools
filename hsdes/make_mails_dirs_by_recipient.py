import os
import re
import json
import argparse
import requests

def mkdir(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def save_recipient_value(recipient_dict, user, field_name, def_field_value, file_name):
    save_value = ''
    if user:
        if user in recipient_dict.keys():
            save_value = recipient_dict[user][field_name]
        else:
            save_value = def_field_value
    else:
        save_value = def_field_value
    with open(file_name, 'w+') as field_file:
        field_file.write(save_value)
    return save_value

def save_file_msg(file_name, msg):
    with open(file_name, 'w+') as msg_file:
        msg_file.write(msg)

def load_dict(dict_file_name):
    with open(dict_file_name, 'r') as dict_file:
        dict_data = json.loads(dict_file.read())
    return dict_data

def update_data_in_results(results_dict, hsdes_recipient_field, recipient_field_value):
    new_results = dict()
    match_data_list = list()
    for data in results_dict['data']:
        if data[hsdes_recipient_field] == recipient_field_value:
            match_data_list.append(data)
        if recipient_field_value == '_no_value' and not data[hsdes_recipient_field]:
            match_data_list.append(data)
    for key in results_dict:
        if key == 'data':
            new_results.update({key:match_data_list})
        elif key == 'total':
            new_results.update({key:len(match_data_list)})
        else:
            new_results.update({key:results_dict[key]})
    return new_results

def main(data_file, recipient_file, hsdes_recipient_field, def_email, out_data_file):
    exit_code = 1
    results = load_dict(data_file)
    recipient_dict = load_dict(recipient_file)
    recipient_set = set()
    mkdir('mails')
    if int(results['total']) > 0:
        if hsdes_recipient_field in results['data'][0].keys():
            for bug in results['data']:
                if bug[hsdes_recipient_field]:
                    recipient_set.add(bug[hsdes_recipient_field])
                else:
                    recipient_set.add('_no_value')
        for recipient in recipient_set:
            recipient_dir = 'mails/' + recipient
            mkdir(recipient_dir)
            recipient_dir += '/'
            save_recipient_value(recipient_dict, recipient, 'email', def_email, recipient_dir + 'email.txt')
            save_recipient_value(recipient_dict, recipient, 'mgr_email', def_email, recipient_dir + 'mgr_email.txt')
            save_recipient_value(recipient_dict, recipient, 'EmpType', 'NONE', recipient_dir + 'EmpType.txt')
            save_recipient_value(recipient_dict, recipient, 'name', recipient, recipient_dir + 'name.txt')
            save_recipient_value(recipient_dict, recipient, 'first_name', recipient, recipient_dir + 'first_name.txt')
            with open(recipient_dir + out_data_file, 'w+') as results_file:
                results_file.write(json.dumps(update_data_in_results(results, hsdes_recipient_field, recipient)))
        save_file_msg('mails/vars_list.txt', 'email,mgr_email,EmpType,name,first_name')
        exit_code = 0
    else:
        save_file_msg('hsdes_query_error.txt', 'no query data')
    return exit_code

if __name__ == '__main__':
    print(os.path.abspath(os.getcwd()))
    print(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument('-d', help='hsdes data file default=hsdes_query_data.json ', required=False, default='hsdes_query_data.json')
    ap.add_argument('-r', help='recipient dict file default=recipient_dict.json ', required=False, default='recipient_dict.json')
    ap.add_argument('-f', help='hsdes recipient field name default=owner', required=False, default='owner')
    ap.add_argument('-email', help='default email if no owner or faceless account default=jonasz.wojcik@intel.com', required=False, default='jonasz.wojcik@intel.com')
    ap.add_argument('-o', help='hsdes data output file default=hsdes_mail_data.json ', required=False, default='hsdes_mail_data.json')
    parsed = ap.parse_args()
    EXIT_CODE = main(parsed.d, parsed.r, parsed.f, parsed.email, parsed.o)
    exit(EXIT_CODE)
