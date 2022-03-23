import json
import requests
from operator import itemgetter
#http://gtax-gcmxd-fm.intel.com/api/v1/


gtax_instance = 'gtax-igk'

def set_gtax_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.put(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def set_gtax_property(gtax_instance, client_id, property_name, property_value):
    url = f'http://{gtax_instance}.intel.com/api/v1/clients/{client_id}/properties/user/{property_name}'
    response = set_gtax_data(url, property_value)
    status = False
    if response == 200:
        status = True
    return status

'''
clients_list = get_clients_properties()
print(f'property:{property_name}')

for client in sorted(clients_list, key=itemgetter(0)):
    print(f"{client[0]}:{client[1]}")
'''

set_gtax_data('http://gtax-igk.intel.com/api/v1/clients/3820/properties/user/discrete_eu_count', '128')

