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

def cut_regression_build_label(xml_string):
    start_label = xml_string.find('<dict>') + 6
    end_label = xml_string.find('</dict>')
    return xml_string[start_label:end_label]

def render_key_value(key, key_value):
    if key == 'regression_build_label' and bool(re.search('^<\?xml version=\"1\.0\" \?\>', key_value)):
        rendered_value = cut_regression_build_label(key_value)
    else:
        rendered_value = str(key_value)
    return rendered_value

def main(data_file, recipient_file, hsdes_recipient_field, def_email):
    exit_code = 1
    results = load_dict(data_file)
    recipient_dict = load_dict(recipient_file)
    mkdir('mails')
    if int(results['total']) > 0:
        if hsdes_recipient_field in results['data'][0].keys():
            for bug in results['data']:
                mkdir('mails/' + str(bug['id']))
                for key in bug.keys():
                    with open('mails/' + str(bug['id']) + '/' + key + '.txt', 'w+') as field_file:
                        field_file.write(render_key_value(key, bug[key]))
                save_recipient_value(recipient_dict, bug[hsdes_recipient_field], 'email', def_email, 'mails/' + str(bug['id']) + '/email.txt')
                save_recipient_value(recipient_dict, bug[hsdes_recipient_field], 'mgr_email', def_email, 'mails/' + str(bug['id']) + '/mgr_email.txt')
                save_recipient_value(recipient_dict, bug[hsdes_recipient_field], 'name', 'no_value', 'mails/' + str(bug['id']) + '/name.txt')
                save_recipient_value(recipient_dict, bug[hsdes_recipient_field], 'first_name', 'no_value', 'mails/' + str(bug['id']) + '/first_name.txt')
                save_recipient_value(recipient_dict, bug[hsdes_recipient_field], 'EmpType', 'NONE', 'mails/' + str(bug['id']) + '/EmpType.txt')
        vars_list = ','.join(results['data'][0].keys()) + ',email,mgr_email,name,first_name,EmpType'
        save_file_msg('mails/vars_list.txt', vars_list)
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
    parsed = ap.parse_args()
    EXIT_CODE = main(parsed.d, parsed.r, parsed.f, parsed.email)
    exit(EXIT_CODE)
