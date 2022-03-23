import sys
import os.path
import argparse
import json
import requests
from datetime import datetime

def main(gtax_instance, client_search_string, is_csq, action, is_list_mode, filter_offline):
    clients_dict = get_clients(gtax_instance, client_search_string, is_csq, filter_offline) 
    print(f'clients found: {len(clients_dict)} {offline_msg(filter_offline)}')
    for client in clients_dict:
        print(f'{action} client {client["name"]} ({client["id"]}) [{client["status"]}]')
        if is_list_mode:
            print('list mode - no changes on client!')
        else:
            url = f'http://{gtax_instance}.intel.com/api/v1/clients/{client["id"]}/{action}'
            if post_gtax_data(url,None):
                print('successful')
            else:
                print('false!! not set!!')
    return 0

def offline_msg(filter_offline):
    offline_text = ''
    if filter_offline:
        if filter_offline == 'skip':
            offline_text = '[offline clients skipped!]'
        if filter_offline == 'only':
            offline_text = '[offline clients only!]'
    return offline_text

def get_clients(gtax_instance, client_search_string, is_csq, filter_offline):
    clients = list()
    if client_search_string:
        print(f'getting data for clients {client_search_string}')
        if is_csq:
            client_search_string = client_search_string.replace(' ','%20')
            client_search_string = client_search_string.replace('=','%3D')
            url = f'http://{gtax_instance}.intel.com/api/v1/clients?csq={client_search_string}&include_all_properties=false&full_info=false&order_by=name'
        else:
            url = f'http://{gtax_instance}.intel.com/api/v1/clients?include_all_properties=false&full_info=false&name={client_search_string}&order_by=name'
        data = get_gtax_data(url)
        for client in data['data']:
            if filter_offline:
                if filter_offline == 'skip':
                    if client['status'] != 'offline':
                        clients.append({'id':client['id'], 'name':client['name'], 'status':client['status']})
                if filter_offline == 'only':
                    if client['status'] == 'offline':
                        clients.append({'id':client['id'], 'name':client['name'], 'status':client['status']})
            else:
                clients.append({'id':client['id'], 'name':client['name'], 'status':client['status']})
    return clients

def post_gtax_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.post(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
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
    usage_msg = '''run_clients_action.exe -s GK-RKL%% -a provision
       run_clients_action.exe -s FM-RKL%% -a power_on -i gtax-gcmxd-fm -offline only
       run_clients_action.exe -csq ('platform' = 'Rocket Lake') -i gtax-gcmxd-fm -csq -a recover
       run_clients_action.exe -h'''
    ap = argparse.ArgumentParser(usage=usage_msg)
    ap.add_argument('-i', '-instance', default='gtax-igk', help='gtax instance:[gtax-igk, gtax-gcmxd-fm, gtax-ril-fm]', required=False)
    ap.add_argument('-s', '-search', help="search clients by name: GK-RKL%%", required=False)
    ap.add_argument('-csq', help="csq query: ('pool' = 'CI_RKL') AND ('platform' = 'Rocket Lake')", required=False)
    ap.add_argument('-a', '-action', nargs='?', choices=['power_off', 'power_on', 'provision', 'recover'], help="action", required=True) # todo reboot hard/soft offline
    ap.add_argument('-offline', default=False, const='all', nargs='?', choices=['skip', 'only'],help='offline clients skip or only', required=False)
    ap.add_argument('-l', '-list', action='store_true', default=False, help='list only mode (no changes on clients)', required=False)
    parsed = ap.parse_args()
    #print(parsed)
    log_script_call()
    if not (parsed.s or parsed.csq):
        ap.error('\nNo params! Use -s or -csq')
    else:
        if parsed.s:
            main(parsed.i, parsed.s, False, parsed.a, parsed.l, parsed.offline)
        if parsed.csq:
            main(parsed.i, parsed.csq, True, parsed.a, parsed.l, parsed.offline)
     
