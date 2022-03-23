import sys
import os.path
import math
import argparse
from datetime import datetime
import json
import requests
import pickle
import pandas as pd

def main(client_search_string, grouping_list, gtax_url, query_mode, filter_offline, use_cache, output_file):
    cache_file_name = 'get_clients_stat_data.cache'
    clients_data = list()
    if use_cache == True and os.path.isfile(cache_file_name):
        with open(cache_file_name, 'rb') as cache:
            clients_data = pickle.load(cache)
    else:
        if query_mode == 'name':
            clients_data = get_clients_data(gtax_url, client_search_string, False, filter_offline)
        if query_mode == 'csq':
            clients_data = get_clients_data(gtax_url, client_search_string, True, filter_offline)
        with open(cache_file_name, 'w+b') as cache:
            pickle.dump(clients_data, cache) 
    if len(clients_data) > 0:
        clients_data_list = clients_data_2_list_dict(clients_data)
        get_clients_stat(clients_data_list, grouping_list, output_file)
    return 0

def get_clients_data(gtax_url, client_search_string, is_csq, filter_offline):
    clients_data = list()
    if client_search_string:
        print(f'getting data for clients {client_search_string} from {gtax_url}')
        if is_csq:
            client_search_string = client_search_string.replace(' ','%20')
            client_search_string = client_search_string.replace('=','%3D')
            url = f'{gtax_url}/api/v1/clients?csq={client_search_string}&include_all_properties=true&full_info=true&order_by=name'
        else:
            url = f'{gtax_url}/api/v1/clients?include_all_properties=true&full_info=true&name={client_search_string}&order_by=name'
        data = get_gtax_data(url)
        if data:
            for client in data['data']:
                if filter_offline:
                    if filter_offline == 'skip' and client['status'] != 'offline':
                            clients_data.append(client)
                    if filter_offline == 'only' and client['status'] == 'offline':
                            clients_data.append(client)
                else:
                    clients_data.append(client)
            print(f'clients found: {len(clients_data)} {offline_msg(filter_offline)}')
        else:
            print(f'no clients found!')
    return clients_data

def offline_msg(filter_offline):
    offline_text = ''
    if filter_offline:
        if filter_offline == 'skip':
            offline_text = '[offline clients skipped!]'
        if filter_offline == 'only':
            offline_text = '[offline clients only!]'
    return offline_text

def get_gtax_instance_url(gtax_instance, gtax_port):
    gtax_instance_url = f'http://{gtax_instance}.intel.com'
    if len(gtax_port) > 1:
        gtax_instance_url += f':{gtax_port}'
    return gtax_instance_url

def get_gtax_data(url):
    gtax_data = None
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    if response.status_code == 200:
        gtax_data = response.json()
    else:
        print(url)
        print(f'status code:{response.status_code}')
        print(response.text)
    return gtax_data
 
def get_client_property_value(property_name, client_data):
    client_property_value = None
    for client_property in client_data['properties']:
        if client_property['property']['name'] == property_name:
            client_property_value = client_property['property']['value']
            break
    return client_property_value

def clients_data_2_list_dict(clients_data):
    clients_data_list = list()
    if clients_data:
        for client in clients_data:
            client_property_list = list()
            for key in ['name', 'id', 'status', 'active_runner', 'is_reserved', 'is_dirty']:
                client_property_dict = dict()
                client_property_dict.update({'name':f'client_{key}'})
                client_property_dict.update({'value':client[key]})
                client_property_dict.update({'type':'system'})
                client_property_dict.update({'active': True})
                client_property_dict.update({'required':False})
                client_property_list.append(client_property_dict)
            for client_property in client['properties']:
                client_property_dict = dict()
                for key in ['name', 'value']:
                    client_property_dict.update({key:client_property['property'][key]})
                for key in ['type', 'active', 'required']:
                    client_property_dict.update({key:client_property[key]})
                if client_property_dict['name'] == 'physical_memory_size':
                    client_property_list.append(get_ram_size(client_property_dict['value']))
                client_property_list.append(client_property_dict)
            for setting in client['settings']:
                client_setting_dict = dict()
                client_setting_dict.update({'name':f"[{setting['name']}]"})
                client_setting_dict.update({'value':setting['value']})
                client_setting_dict.update({'type':'setting'})
                client_setting_dict.update({'active':'True'})
                client_setting_dict.update({'required':'False'})
                client_property_list.append(client_setting_dict)
            clients_data_list.append(client_property_list)
    return clients_data_list

def get_ram_size(physical_memory_size):
    ram_size_value = calc_ram_size(physical_memory_size)
    ram_size_dict = dict()
    ram_size_dict.update({'name': 'ram_size'})
    ram_size_dict.update({'value': ram_size_value})
    ram_size_dict.update({'type': 'auto_detected'})
    ram_size_dict.update({'active': True})
    ram_size_dict.update({'required': False})
    return ram_size_dict

def calc_ram_size(physical_memory_size):
    ram_size_value = int(math.ceil(int(physical_memory_size)/1024/1024/1024))
    if ram_size_value % 2 > 0:
        ram_size_value +=1
    return str(ram_size_value)

def get_all_clients_data_keys(clients_data_list, select=all):
    keys_set = set()
    all_keys = list()
    for client_data in clients_data_list:
        for i in range(len(client_data)):
            if select == 'all_auto' and client_data[i]['type'] == 'auto_detected':
                keys_set.add(client_data[i]['name'])
            elif select == 'all_user' and client_data[i]['type'] == 'user_defined':
                keys_set.add(client_data[i]['name'])
            elif select == 'all_system' and client_data[i]['type'] == 'system':
                keys_set.add(client_data[i]['name'])
            elif select == 'all_required' and client_data[i]['required'] == True:
                keys_set.add(client_data[i]['name'])
            elif select == 'all' and client_data[i]['type'] != 'setting':
                keys_set.add(client_data[i]['name']) 
            elif select == 'all_settings' and client_data[i]['type'] == 'setting':
                keys_set.add(client_data[i]['name']) 
    for key in ['client_name', 'client_id', 'client_status', 'client_active_runner', 'client_is_reserved', 'client_is_dirty']:
        if key in keys_set:
            keys_set.remove(key)
            all_keys.append(key)
    for key in sorted(keys_set):
        all_keys.append(key)
    return all_keys

def get_client_property(client_data, property_name, property_key):
    user_present = False
    property_value = ''
    #check user first
    for i in range(len(client_data)):
        if property_name == client_data[i]['name'] and client_data[i]['type'] == 'user_defined':
            property_value = client_data[i][property_key]
            user_present = True
            break
    #then check auto if not user
    if not user_present:
        for i in range(len(client_data)):
            if property_name == client_data[i]['name']:
                property_value = client_data[i][property_key]
                break
    return property_value

def get_clients_stat(clients_data_list, grouping_list, output_file):
    df_clients = convert2df(clients_data_list)
    print(f'grouping stat: {grouping_list}')
    get_stat(df_clients, grouping_list, output_file)
    return 0

def get_stat(df_clients, stat_group, output_file):
    clients_stat = pd.DataFrame(df_clients.groupby(stat_group)['count'].count())
    print(df_2_html(clients_stat, output_file))

def convert2df(clients_data_list):
    clients_list = list()
    for client_data_list in clients_data_list:
        client_data_dict = dict()
        for data in client_data_list:
            if data['type'] in ['auto_detected', 'system', 'setting']:
                client_data_dict.update({data['name']:data['value']})
                if data['name'] == 'client_id':
                    client_data_dict.update({'count':1})
        for data in client_data_list:
            if data['type'] == 'user_defined':
                client_data_dict.update({data['name']:data['value']})
        clients_list.append(client_data_dict)
    return pd.DataFrame(clients_list)

def df_2_html(df, file_name):
    app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    stat_path = os.path.join(app_path, 'stat')
    stat_file = os.path.join(stat_path, file_name)
    html = '<!DOCTYPE html><html><head><style>table {font-family:Verdana;font-size: 10px; border-collapse: collapse;} table, th, td {border: 1px solid black; padding-left: 5px; padding-right: 5px; padding-top: 2px; padding-bottom: 2px;} tr:nth-child(even) {background-color: #f2f2f2;}</style></head><body><div style="overflow-x:auto;">'
    html += df.to_html()
    html += '</div></body></html>' 
    if not os.path.exists(stat_path):
        os.makedirs(stat_path)
    with open(stat_file, 'w') as out_file:
        out_file.write(html)
    return f'file saved: {stat_file}'

def get_filename_timestamp():
    ts = str(datetime.now())
    ts = ts.replace(':', '_')
    return ts[5:-7]

def print_tabs_config_template():
    template_file = 'tabs_template.json'
    tabs_template = {'tabs':[{'name': 'clients', 'columns': 'client_name,client_id,label_id,client_status,pool,board_name,platform'}, {'name': 'displays', 'columns': 'display_external,display_hdmi,display_dp,display_edp,display_raritan,display_id,display_dp_id,display_hdmi_id,display_raritan_id,display_raritan_connected_port,kvm'}, {'name': 'user', 'columns': 'all_user'}, {'name': 'required', 'columns': 'all_required'}, {'name': 'settings', 'columns': 'all_settings'}]}
    with open(template_file, 'w') as outfile:
        json.dump(tabs_template, outfile, indent=4)
    print(json.dumps(tabs_template, indent=4))
    print(f'template saved:{template_file}')

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
    ts = get_filename_timestamp()
    ap = argparse.ArgumentParser()
    ap.add_argument('-i', '-instance', default='gtax-igk', help='gtax instance:[gtax-igk, gtax-gcmxd-fm, gtax-ril-fm]', required=False)
    ap.add_argument('-p', '-port', default='', help='gtax instance port', required=False)
    ap.add_argument('-n', '-name', help="search clients by name: GK-RKL%%", required=False)
    ap.add_argument('-csq', help="csq query: ('pool' = 'CI_RKL')", required=False) 
    ap.add_argument('-c', '-columns', default='pool', help='columns list: [all/all_auto/all_user/all_settings/client_name,label_id,client_status,pool]', required=False)
    ap.add_argument('-o', '-output', default=None, help='output file name', required=False)
    ap.add_argument('-offline', default=False, const='all', nargs='?', choices=['skip', 'only'], help='offline clients skip or only', required=False)
    ap.add_argument('-cache', action='store_true', default=False, help='use cache from last call (no gtax call)', required=False)
    
    parsed = ap.parse_args()
    gtax_url = get_gtax_instance_url(parsed.i, parsed.p)
    log_script_call()
    grouping_list = parsed.c.split(',')
    if not (parsed.n or parsed.csq):
        ap.error('\nNo params! Use -n or -csq')
    else:
        search_string = ''
        query_mode = 'name'
        cloumns_string = ''
        if parsed.n: 
            query_mode = 'name'
            search_string = parsed.n
        if parsed.csq: 
            query_mode = 'csq'
            search_string = parsed.csq
        if parsed.o:
            output_file = parsed.o
        else:
            output_file = f"stat_{parsed.i}{ts}_{'-'.join(grouping_list)}.html"
        main(search_string, grouping_list, gtax_url, query_mode, parsed.offline, parsed.cache, output_file)
