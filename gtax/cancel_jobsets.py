import sys
import os.path
import argparse
import json
import requests
from datetime import datetime

def main(gtax_instance, jobset_ids, notes, is_list_mode):
    jobset_id_list = jobset_ids.split(',')
    for jobset_id in jobset_id_list:
        print(f'canceling jobset:{jobset_id} with note: {notes}')
        if is_list_mode:
            print('list mode - no changes in gtax!')
        else:
            if cancel_gtax_jobset(gtax_instance, jobset_id, notes):
                print('successful')
            else:
                print('false!! not set!!')
    return 0

def cancel_gtax_jobset(gtax_instance, jobset_id, notes):
    url = f'http://{gtax_instance}.intel.com/api/v1/jobsets/{jobset_id}/cancel'
    notes_data = f'"notes": "{notes}"'
    data = '{' + notes_data + '}'
    response = put_gtax_data(url, data)
    if response.status_code == 200:
        status = True
    else:
        status = False
        print(response)
    return status

def put_gtax_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.put(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def delete_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.delete(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def get_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response.json()

def log_script_call():
    app_name = os.path.basename(sys.argv[0])
    app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    log_path = os.path.join(app_path, 'logs')
    params_list = sys.argv[1:]
    call_log_file = os.path.join(log_path, f"{app_name.split('.')[0]}_calls.log")
    command = f'{app_name}'
    for param in params_list:
        if param.find(chr(39)) > 0 or param.find(chr(32)) > 0:
            command += f' "{param}"'
        else:
            command += f' {param}'
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    with open(call_log_file, 'a') as log_file:
        log_file.write(f'[{str(datetime.now())}] {command}\n')

if __name__ == '__main__':
    usage_msg = '''cancel_jobsets.exe -j "123456789,123456790"
       cancel_jobsets.exe -j "123456789,123456790" -n "my custom cancel note"
       cancel_jobsets.exe -j -i gtax-gcmxd-fm  "123456789,123456790" -n "my custom cancel note" -l'''
    ap = argparse.ArgumentParser(usage=usage_msg)
    ap.add_argument('-i', '-instance', default='gtax-igk', help='gtax instance:[gtax-igk, gtax-gcmxd-fm, gtax-ril-fm]', required=False)
    ap.add_argument('-j', '-jobsets', help='coma seperated jobset ids exp: "123456789,123456790"', required=True)
    ap.add_argument('-n', '-note', default="canceled by CI team", help='cancel note', required=False)
    ap.add_argument('-l', '-list', action='store_true', default=False, help='list only mode (no changes on clients)', required=False)
    parsed = ap.parse_args()
    #print(parsed)
    log_script_call()
    main(parsed.i, parsed.j, parsed.n, parsed.l)
    