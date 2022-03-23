import sys
import os.path
import argparse
import json
import requests
from datetime import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def main(gtax_instance, client_search_string, replace_from, replace_to, is_csq, is_list_mode, filter_offline, update_netbox):
    clients_dict = get_clients(gtax_instance, client_search_string, is_csq, filter_offline, update_netbox) 
    print(f'clients found: {len(clients_dict)} {offline_msg(filter_offline)}')
    for client in clients_dict:
        info_text = f'replace name {client["name"]} to {client["name"].replace(replace_from, replace_to)} on ({client["id"]}) [{client["status"]}]'
        if update_netbox:
            info_text +=  f' - netbox_id: {client["netbox_id"]}'
        print(info_text)
        if is_list_mode:
            print('list mode - no changes on client!')
        else:
            if replace_client_name(gtax_instance, client["id"], client["name"], replace_from, replace_to, update_netbox, client["netbox_id"]):
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

def get_clients(gtax_instance, client_search_string, is_csq, filter_offline, update_netbox):
    clients = list()
    netbox_id = None
    full_info = 'false'
    if update_netbox:
        full_info = 'true'
    if client_search_string:
        print(f'getting data for clients {client_search_string}')
        if is_csq:
            client_search_string = client_search_string.replace(' ','%20')
            client_search_string = client_search_string.replace('=','%3D')
            url = f'http://{gtax_instance}.intel.com/api/v1/clients?csq={client_search_string}&include_all_properties=false&full_info={full_info}&order_by=name'
        else:
            url = f'http://{gtax_instance}.intel.com/api/v1/clients?include_all_properties=false&full_info={full_info}&name={client_search_string}&order_by=name'
        data = get_gtax_data(url)
        for client in data['data']:
            if update_netbox:
                netbox_id = None
                for prop in client['properties']:
                    if prop['property']['name'] == 'netbox_id':
                        netbox_id = prop['property']['value'].replace('/', '')[-4:]
                if netbox_id is None:
                    print('no netbox_id found!')
            if filter_offline:
                if filter_offline == 'skip':
                    if client['status'] != 'offline':
                        clients.append({'id':client['id'], 'name':client['name'], 'status':client['status'], 'netbox_id':netbox_id})
                if filter_offline == 'only':
                    if client['status'] == 'offline':
                        clients.append({'id':client['id'], 'name':client['name'], 'status':client['status'], 'netbox_id':netbox_id})
            else:
                clients.append({'id':client['id'], 'name':client['name'], 'status':client['status'], 'netbox_id':netbox_id})
    return clients

def replace_client_name(gtax_instance, client_id, client_name, replace_from, replace_to, update_netbox, netbox_id):
    new_name = client_name.replace(replace_from, replace_to)
    if new_name == client_name:
        print(f'no name change in gtax for {client_name} - {replace_from} not found in name')
        status_gtax = False
    else:
        response = update_gtax_name(gtax_instance, client_id, new_name)
        if response.status_code == 200:
            status_gtax = True
            print('gtax OK')
        else:
            status_gtax = False
            print(response)
    status = status_gtax
    if update_netbox and netbox_id:
        if get_netbox_name(netbox_id) == new_name:
            print(f'no name change in netbox for {client_name} - {replace_from} not found in name')
            status_netbox = False
        else:
            response = update_netbox_name(netbox_id, new_name)
            if response.status_code == 200:
                if get_netbox_name(netbox_id) == new_name:
                    print('netbox OK')
                    status_netbox = True
                else:
                    print('netbox FAIL!')
                    status_netbox = False
            else:
                status_netbox = False
                print(response)
        status = status and status_netbox
    return status

def update_gtax_name(gtax_instance, client_id, new_name):
    url = f'http://{gtax_instance}.intel.com/api/v1/clients/{client_id}'
    data = f'{{\"name\": \"{new_name}\"}}'
    response = put_gtax_data(url, data)
    return response

def get_netbox_name(netbox_id):
    netbox_name = None
    url = f'https://netbox.igk.intel.com/api/dcim/devices/{netbox_id}/'
    response = get_netbox_data(url)
    if response.status_code == 200:
        data = response.json()
        netbox_name = data['name']
    else:
        print(response)
    return netbox_name

def update_netbox_name(netbox_id, new_name):
    netbox_url = f'https://netbox.igk.intel.com/api/dcim/devices/{netbox_id}/'
    data = f'{{\"name\": \"{new_name}\"}}'
    response = patch_netbox_data(netbox_url, data)
    return response

def patch_netbox_data(url, data):
    headers = {'Authorization': 'Token be9ff04162d1ef2a5c4726255b11cb2858439f05', 'accept': 'application/json', 'Content-Type': 'application/json'}
    response = requests.patch(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912'}, verify=False)
    return response

def get_netbox_data(url):
    headers = {'Authorization': 'Token be9ff04162d1ef2a5c4726255b11cb2858439f05', 'accept': 'application/json', 'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912'}, verify=False)
    return response

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
    usage_msg = '''replace_clients_name.exe -s GK-RKL%% -f RKL -t RKL-S
       replace_clients_name.exe -s FM-RKL%% -i gtax-gcmxd-fm -f RKL -t RKL-S -l
       replace_clients_name.exe -csq ('platform' = 'Rocket Lake') -i gtax-gcmxd-fm -f RKL -t RKL-S -offline skip'''
    ap = argparse.ArgumentParser(usage=usage_msg)
    ap.add_argument('-i', '-instance', default='gtax-igk', help='gtax instance:[gtax-igk, gtax-gcmxd-fm, gtax-ril-fm]', required=False)
    ap.add_argument('-s', '-search', help="search clients by name: GK-RKL%%", required=False)
    ap.add_argument('-csq', help="csq query: ('pool' = 'CI_RKL') AND ('platform' = 'Rocket Lake')", required=False)
    ap.add_argument('-f', '-from', help='name phrase to replace from', required=True)
    ap.add_argument('-t', '-to', help='name phrase to replace to', required=True)
    ap.add_argument('-l', '-list', action='store_true', default=False, help='list only mode (no changes on clients)', required=False)
    ap.add_argument('-offline', default=False, const='all', nargs='?', choices=['skip', 'only'], help='offline clients skip or only', required=False)
    ap.add_argument('-n', '-netbox', action='store_true', default=False, help='update name in netbox', required=False)
    parsed = ap.parse_args()
    #print(parsed)
    log_script_call()
    if not (parsed.s or parsed.csq):
        ap.error('\nNo params! Use -s or -csq')
    else:
        if parsed.s:
            main(parsed.i, parsed.s, parsed.f, parsed.t, False, parsed.l, parsed.offline, parsed.n)
        if parsed.csq:
            main(parsed.i, parsed.csq, parsed.f, parsed.t, True, parsed.l, parsed.offline, parsed.n)
