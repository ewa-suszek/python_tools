import sys
import os.path
import argparse
import json
import requests

def main(gtax_instance, client_search_string, is_csq, is_list_mode):
    clients_dict = get_clients(gtax_instance, client_search_string, is_csq) 
    print(f'clients found: {len(clients_dict)}')
    for client in clients_dict:
        print(f'provision client {client["name"]} ({client["id"]})')
        if is_list_mode:
            print('list mode - no changes on client!')
        else:
            url = f'http://{gtax_instance}.intel.com/api/v1/clients/{client["id"]}/provision'
            if post_gtax_data(url,None):
                print('successful')
            else:
                print('false!! not set!!')
    return 0

def get_clients(gtax_instance, client_search_string, is_csq):
    clients = list()
    if client_search_string:
        print(f'getting data for clients {client_search_string}')
        if is_csq:
            client_search_string = client_search_string.replace(' ','%20')
            client_search_string = client_search_string.replace('=','%3D')
            url = f'http://{gtax_instance}.intel.com/api/v1/clients?csq={client_search_string}&include_all_properties=false&full_info=false&order_by=id'
        else:
            url = f'http://{gtax_instance}.intel.com/api/v1/clients?include_all_properties=false&full_info=false&name={client_search_string}&order_by=id'
        data = get_gtax_data(url)
        for client in data['data']:
            clients.append({'id':client['id'], 'name':client['name']})
    return clients

def post_gtax_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.post(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def get_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response.json()

if __name__ == '__main__':
    usage_msg = '''provision_clients.exe -s GK-RKL%% 
       provision_clients.exe -s FM-RKL%% -i gtax-gcmxd-fm
       provision_clients.exe -s ('platform' = 'Rocket Lake') -i gtax-gcmxd-fm -csq'''
    ap = argparse.ArgumentParser(usage=usage_msg)
    ap.add_argument('-i', '-instance', default='gtax-igk', help='gtax instance:[gtax-igk, gtax-gcmxd-fm, gtax-ril-fm]', required=False)
    ap.add_argument('-s', '-search', help="search clients by name: GK-RKL%% or csq query with -csq switch: ('pool' = 'CI_RKL') AND ('platform' = 'Rocket Lake')", required=True)
    ap.add_argument('-l', '-list', action='store_true', default=False, help='list only mode (no changes on clients)', required=False)
    ap.add_argument('-csq', action='store_true', default=False, help='csq mode -s (csq query)', required=False) 
    parsed = ap.parse_args()
    #print(parsed)
    if parsed.s:
        main(parsed.i, parsed.s, parsed.csq, parsed.l)
