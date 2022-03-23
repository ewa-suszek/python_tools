import sys
import os.path
import argparse
import json
import requests
from datetime import datetime

def main(gtax_instance_from, gtax_instance_to, client_search_string, is_csq, is_list_mode, filter_offline):
    clients_dict = get_clients(gtax_instance_from, client_search_string, is_csq, filter_offline) 
    print(f'clients found: {len(clients_dict)} {offline_msg(filter_offline)}')
    for client in clients_dict:
        print(f'moving {client["name"]} ({client["id"]}) [{client["status"]}] [{client["address"]}] form {gtax_instance_from} to {gtax_instance_to}')
        if is_list_mode:
            print('list mode - no changes on client!')
        else:
            old_settings = client["settings"]
            user_properties = client["user_properties"]
            user_properties_req = client["user_properties_req"]
            print(f'adding client to {gtax_instance_to}')
            new_client_id = add_gtax_client(gtax_instance_to, client["name"], client["address"])
            if new_client_id:
                print(f'removing client from {gtax_instance_from}')
                remove_client(gtax_instance_from, client['id'], f'moving to {gtax_instance_to}')
                new_settings = get_gtax_settings(gtax_instance_to, new_client_id)
                old_settings.update({'service_url':new_settings['service_url']})
                old_settings.update({'client_id':new_settings['client_id']})
                print(f'updating client data on {gtax_instance_to}')
                set_gtax_settings(gtax_instance_to, new_client_id, old_settings)
                set_gtax_user_properties(gtax_instance_to, new_client_id, user_properties)
                for key in user_properties_req.keys():
                    set_gtax_property(gtax_instance_to, new_client_id, key, user_properties_req[key], True)
                print(f'client added to {gtax_instance_to} as {client["name"]} id:{new_client_id} http://{gtax_instance_to}.intel.com/#/clients/{new_client_id}')
            else:
                print(f'client not added - aborted to remove from {gtax_instance_from}')
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
            url = f'http://{gtax_instance}.intel.com/api/v1/clients?csq={client_search_string}&include_all_properties=true&full_info=true&order_by=name'
        else:
            url = f'http://{gtax_instance}.intel.com/api/v1/clients?include_all_properties=true&full_info=true&name={client_search_string}&order_by=name'
        data = get_gtax_data(url)
        for client in data['data']:
            if filter_offline:
                if filter_offline == 'skip':
                    if client['status'] != 'offline':
                        clients.append(add_client_data(client))
                if filter_offline == 'only':
                    if client['status'] == 'offline':
                        clients.append(add_client_data(client))
            else:
                clients.append(add_client_data(client))
    return clients

def add_client_data(client):
    client_settings = dict()
    user_properties = dict()
    user_properties_req = dict()
    for setting in client['settings']:
        client_settings.update({setting['name']:setting['value']})
    for prop in client['properties']:
        if prop['type'] == 'user_defined':
            if prop['required']:
                user_properties_req.update({prop['property']['name']:prop['property']['value']})
            else:
                user_properties.update({prop['property']['name']:prop['property']['value']})
    return {'id':client['id'], 'name':client['name'], 'status':client['status'], 'agent_type':client['agent_type'], 'address':client['address'], 'settings':client_settings, 'user_properties':user_properties, 'user_properties_req':user_properties_req}

def set_gtax_settings(gtax_instance, client_id, settings_dict):
    url = f'http://{gtax_instance}.intel.com/api/v1/clients/{client_id}/settings'
    data = str(settings_dict).replace('\'','"')
    response = put_gtax_data(url, data)
    if response.status_code == 200:
        status = True
    else:
        status = False
        print(response)
    return status

def get_gtax_settings(gtax_instance, client_id):
    url = f'http://{gtax_instance}.intel.com/api/v1/clients/{client_id}/settings'
    settings_dict = get_gtax_data(url)
    return settings_dict

def set_gtax_user_properties(gtax_instance, client_id, properties_dict):
    url = f'http://{gtax_instance}.intel.com/api/v1/clients/{client_id}/properties/user'
    data = str(properties_dict).replace('\'','"')
    response = put_gtax_data(url, data)
    if response.status_code == 200:
        status = True
    else:
        status = False
        print(response)
    return status

def set_gtax_property(gtax_instance, client_id, property_name, property_value, is_required):
    url = f'http://{gtax_instance}.intel.com/api/v1/clients/{client_id}/properties/user/{property_name}'
    property_value = f'"value": "{property_value}", "required": {str(is_required).lower()}'
    data = '{' + property_value + '}'
    response = put_gtax_data(url, data)
    if response.status_code == 200:
        status = True
    else:
        status = False
        print(response)
    return status

def add_gtax_client(gtax_instance, client_name, client_address):
    new_id = None
    data = '{'
    data += f'"name": "{client_name}",'
    data += f'"type": "tc",'
    data += f'"address": "{client_address}",'
    data += f'"environment": "silicon"'
    data += '}'
    url = f'http://{gtax_instance}.intel.com/api/v1/clients'
    response = post_gtax_data(url, data)
    if response.status_code == 200:
        new_id = response.text
        print(f'new id:{new_id}')
    else:
        print(response)
    return new_id

def remove_client(gtax_instance, client_id, text_note):
    url = f'http://{gtax_instance}.intel.com/api/v1/clients/{client_id}'
    data = '{'
    data += f'"status_notes": "{text_note}"'
    data += '}'
    delete_gtax_data(url, data)

def put_gtax_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.put(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def post_gtax_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.post(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def delete_gtax_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.delete(url, data=data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
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
    usage_msg = '''move_clients.exe -f gtax-igk -t gtax-igk-smoke -s GK-RKL001
       move_clients.exe -f gtax-igk -t gtax-igk-smoke -s GK-RKL001 -l
       move_clients.exe -f gtax-igk -t gtax-igk-smoke -csq "('lab_notes' = 'move_to_smoke')" -offline skip'''
    ap = argparse.ArgumentParser(usage=usage_msg)
    ap.add_argument('-f', '-instance_from', default='gtax-igk', help='gtax instance:[gtax-igk, gtax-gcmxd-fm, gtax-ril-fm]', required=False)
    ap.add_argument('-t', '-instance_to', default='gtax-igk-smoke', help='gtax instance:[gtax-igk-smoke, gtax-shared-fm]', required=False)
    ap.add_argument('-s', '-search', help="search clients by name: GK-RKL%%", required=False)
    ap.add_argument('-csq', help="csq query: ('lab_notes' = 'move_to_smoke')", required=False)
    ap.add_argument('-l', '-list', action='store_true', default=False, help='list only mode (no changes on clients)', required=False)
    ap.add_argument('-offline', default=False, const='all', nargs='?', choices=['skip', 'only'], help='offline clients skip or only', required=False)
    parsed = ap.parse_args()
    #print(parsed)
    log_script_call()
    if not (parsed.s or parsed.csq):
        ap.error('\nNo params! Use -s or -csq')
    else:
        if parsed.s:
            main(parsed.f, parsed.t, parsed.s, False, parsed.l, parsed.offline)
        if parsed.csq:
            main(parsed.f, parsed.t, parsed.csq, True, parsed.l, parsed.offline)
