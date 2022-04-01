'''
HSDES API DOCS: https://hsdes.intel.com/rest/doc/#!/query/getQuery

exp: prebuild_query_time_data.py  -id 18011272558 -u "idsid" -t "*****************************" -lbt "2020-04-21 02:36:01.258"  -tf "awaiting_development_date" -td 9
'''
import sys
import os.path
import argparse
import json
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
#import urllib3
# this is to ignore the ssl insecure warning as we are passing in 'verify=false'
#urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_hsdes_data(query_id, user, token):
    headers = {'Content-type': 'application/json'}
    url = 'https://hsdes-api.intel.com/rest/auth/query/'+query_id+'?max_results=10000'
    response = requests.get(url, verify=False, auth=HTTPBasicAuth(user, token), headers=headers)
    return response.json()

def is_in_time_range(from_time, to_time, time_to_check_string, time_format):
    time_to_check = datetime.strptime(time_to_check_string, time_format)
    is_in_range = False
    if time_to_check >= from_time and time_to_check <= to_time:
        is_in_range = True
    return is_in_range

def update_data_in_results(results_dict, time_from, time_to, time_field, time_format):
    new_results = dict()
    match_data_list = list()
    for data in results_dict['data']:
        if is_in_time_range(time_from, time_to, data[time_field], time_format):
            match_data_list.append(data)
    for key in results_dict:
        if key == 'data':
            new_results.update({key:match_data_list})
        elif key == 'total':
            new_results.update({key:len(match_data_list)})
        else:
            new_results.update({key:results_dict[key]})
    return new_results

def main(query_id, user, token, data_file, fields_file, size_file, last_build_time='', time_field='', time_diff=9):
    time_format = '%Y-%m-%d %H:%M:%S.%f'
    if last_build_time and time_field:
        time_from = datetime.strptime(last_build_time, time_format) + timedelta(hours=time_diff)
        time_to = datetime.now() + timedelta(hours=time_diff)
        print('query id:' + query_id + ' - time from:' + time_from.strftime(time_format) + ' - time to:' + time_to.strftime(time_format) + ' - time diff:' + str(time_diff) + ' - time field:' + str(time_field))
        results = update_data_in_results(get_hsdes_data(query_id, user, token), time_from, time_to, time_field, time_format)
    else:
        print('query id:' + query_id)
        results = get_hsdes_data(query_id, user, token)
    total = results['total']
    print('found:' + str(total))
    with open(data_file, 'w+') as results_file:
        results_file.write(json.dumps(results))
    with open(size_file, 'w+') as results_size_file:
        results_size_file.write(str(total))
    if total > 0:
        return_code = 0
        table_fields = "'" + "','".join(results['data'][0].keys()) + "'"
        with open(fields_file, 'w+') as table_fields_file:
            table_fields_file.write(table_fields)
    else:
        print('no data exit code = 1')
        return_code = 1
    return return_code

if __name__ == '__main__':
    print(os.path.abspath(os.getcwd()))
    print(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument('-id', help='HSDES article ID exp:1208691365', required=True)
    ap.add_argument('-u', help='user', required=True)
    ap.add_argument('-t', help='token', required=True)
    ap.add_argument('-od', help='output file data default=hsdes_query_data.json', required=False, default='hsdes_query_data.json')
    ap.add_argument('-of', help='output file query fields list default=hsdes_query_table_fields.txt', required=False, default='hsdes_query_table_fields.txt')
    ap.add_argument('-os', help='output file data size default=hsdes_query_data_size.txt', required=False, default='hsdes_query_data_size.txt')
    ap.add_argument('-lbt', help='last build time format: %Y-%m-%d %H:%M:%S.%f', required=False)
    ap.add_argument('-tf', help='time field to compare time exp: update_date', required=False)
    ap.add_argument('-td', help='time difference exp: 9', required=False, type=int, default=9)
    parsed = ap.parse_args()
    exit_code = main(parsed.id, parsed.u, parsed.t, parsed.od, parsed.of, parsed.os, parsed.lbt, parsed.tf, parsed.td)
    exit(exit_code)
