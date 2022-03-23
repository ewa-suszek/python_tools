import json
import requests
from operator import itemgetter
#http://gtax-gcmxd-fm.intel.com/api/v1/


gtax_instance = 'gtax-gcmxd-fm'
clients_search_name = 'FM-RKS-%'
property_string = 'bios_processor_stepping,diva_version'

property_list = property_string.split(',')

print(property_list)

#http://gtax-gcmxd-fm.intel.com/api/v1/clients?job_summary=false&include_runner_details=false&include_reservations=false&include_deleted=false&include_all_properties=false&properties=diva_version&include_group=false&include_job_data=false&full_info=false&name=FM-RKS-%25
#client_1_name = 'FM-RKS-071'
#client_2_name = 'FM-RKS-062'


def get_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def get_clients_properties():
    clients = []
    response = get_gtax_data(f'http://{gtax_instance}.intel.com/api/v1/clients?job_summary=false&include_runner_details=false&include_reservations=false&include_deleted=false&include_all_properties=false&include_group=false&include_job_data=false&full_info=false&properties={property_name}&name={clients_search_name}')
    data = response.json()
    for client in data['data']:
        no_data = True
        if 'properties' in client.keys():
            if client['properties']:
                for property in client['properties']:
                    if property
                #print(f"{client['name']} {client['properties'][0]['property']['name']} {client['properties'][0]['property']['value']}")
                clients.append([client['name'], client['properties'][0]['property']['value']])
                no_data = False
        if no_data:
            clients.append([client['name'], '-------'])
    return clients

clients_list = get_clients_properties()
print(f'property:{property_string.replace(',','\t')}')

for client in sorted(clients_list, key=itemgetter(0)):
    print(f"{client[0]}:{client[1]}")


