import sys
import os.path
import argparse
import json
import requests
from datetime import datetime

def main(gtax_url, client_search_string, property_name, property_value, is_required, is_csq, is_list_mode, filter_offline, remove_property):
    updated_count = 0
    clients_dict = get_clients(gtax_url, client_search_string, is_csq, filter_offline) 
    print(f'clients found: {len(clients_dict)} {offline_msg(filter_offline)}')
    for client in clients_dict:
        if remove_property:
            print(f'removing property {property_name} on {client["name"]} ({client["id"]}) [{client["status"]}]')
        else:
            print(f'setting property {property_name} value {property_value} {req_msg(is_required)} on {client["name"]} ({client["id"]}) [{client["status"]}]')
        if is_list_mode:
            print('list mode - no changes on client!')
        else:
            if remove_property:
                if remove_gtax_property(gtax_url, client["id"], property_name):
                    updated_count += 1
                    print('successful')
                else:
                    print('false!! not removed!!')
            else:
                if set_gtax_property(gtax_url, client["id"], property_name, property_value, is_required):
                    updated_count += 1
                    print('successful')
                else:
                    print('false!! not set!!')
    print(f'total clients: {len(clients_dict)}\ntotal updated: {updated_count}')
    return 0

def offline_msg(filter_offline):
    offline_text = ''
    if filter_offline:
        if filter_offline == 'skip':
            offline_text = '[offline clients skipped!]'
        if filter_offline == 'only':
            offline_text = '[offline clients only!]'
    return offline_text

def req_msg(is_required):
    required_text = ''
    if is_required:
        required_text = 'with required flag'
    return required_text


def get_clients(gtax_url, client_search_string, is_csq, filter_offline):
    clients = list()
    if client_search_string:
        print(f'getting data for clients {client_search_string}')
        if is_csq:
            client_search_string = client_search_string.replace(' ','%20')
            client_search_string = client_search_string.replace('=','%3D')
            url = f'{gtax_url}/api/v1/clients?csq={client_search_string}&include_all_properties=false&full_info=false&order_by=name'
            # to do add option for &ensure_req_match=true
        else:
            url = f'{gtax_url}/api/v1/clients?include_all_properties=false&full_info=false&name={client_search_string}&order_by=name'
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

def set_gtax_property(gtax_url, client_id, property_name, property_value, is_required):
    url = f'{gtax_url}/api/v1/clients/{client_id}/properties/user/{property_name}'
    property_value = f'"value": "{property_value}", "required": {str(is_required).lower()}'
    data = '{' + property_value + '}'
    response = set_gtax_data(url, data)
    if response.status_code == 200:
        status = True
    else:
        status = False
        print(response)
    return status

def remove_gtax_property(gtax_url, client_id, property_name):
    url = f'{gtax_url}/api/v1/clients/{client_id}/properties/user/{property_name}'
    response = delete_gtax_data(url)
    if response.status_code == 200:
        status = True
    else:
        status = False
        print(response)
    return status    

def get_gtax_instance_url(gtax_instance, gtax_port):
    gtax_instance_url = f'http://{gtax_instance}.intel.com'
    if len(gtax_port) > 1:
        gtax_instance_url += f':{gtax_port}'
    return gtax_instance_url    

def set_gtax_data(url, data):
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
    usage_msg = '''add_clients_property.exe -s GK-RKL%% -n property_name -v value
       add_clients_property.exe -s FM-RKL%% -i gtax-gcmxd-fm -n property_name -v value -offline skip
       add_clients_property.exe -csq ('platform' = 'Rocket Lake') -i gtax-gcmxd-fm -n property_name -v value -r'''
    ap = argparse.ArgumentParser(usage=usage_msg)
    ap.add_argument('-i', '-instance', default='gtax-igk', help='gtax instance:[gtax-igk, gtax-gcmxd-fm, gtax-ril-fm]', required=False)
    ap.add_argument('-p', '-port', default='', help='gtax instance port', required=False)
    ap.add_argument('-s', '-search', help="search clients by name: GK-RKL%%", required=False)
    ap.add_argument('-csq', help="csq query: ('pool' = 'CI_RKL') AND ('platform' = 'Rocket Lake')", required=False)
    ap.add_argument('-n', '-name', help='property name', required=True)
    ap.add_argument('-v', '-value', help='property value', required=False)
    ap.add_argument('-r', '-required', action='store_true', default=False, help='set as required', required=False)
    ap.add_argument('-l', '-list', action='store_true', default=False, help='list only mode (no changes on clients)', required=False)
    ap.add_argument('-rem', '-remove', action='store_true', default=False, help='remove property', required=False)
    ap.add_argument('-offline', default=False, const='all', nargs='?', choices=['skip', 'only'], help='offline clients skip or only', required=False)
    parsed = ap.parse_args()
    gtax_url = get_gtax_instance_url(parsed.i, parsed.p)
    log_script_call()
    if not (parsed.s or parsed.csq):
        ap.error('\nNo params! Use -s or -csq')
    else:
        if not (parsed.v or parsed.rem):
            ap.error('\nNo params! Use -v to provide value or -rem to remove')
        else:
            if parsed.s:
                main(gtax_url, parsed.s, parsed.n, parsed.v, parsed.r, False, parsed.l, parsed.offline, parsed.rem)
            if parsed.csq:
                main(gtax_url, parsed.csq, parsed.n, parsed.v, parsed.r, True, parsed.l, parsed.offline, parsed.rem)

        
