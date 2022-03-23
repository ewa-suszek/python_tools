import json
import pickle
import requests
from operator import itemgetter
#http://gtax-gcmxd-fm.intel.com/api/v1/

gtax_instance = 'gtax-gcmxd-fm'

#http://gtax-gcmxd-fm.intel.com/api/v1/clients?job_summary=false&include_runner_details=false&include_reservations=false&include_deleted=false&include_all_properties=false&properties=diva_version&include_group=false&include_job_data=false&full_info=false&name=FM-RKS-%25
#client_1_name = 'FM-RKS-071'
#client_2_name = 'FM-RKS-062'


def get_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def get_all_clients(offline_mode=False):
    clients = []
    if offline_mode:
        with open('gtax_instance_clients.cache', 'rb') as cache:
            clients = pickle.load(cache)
    else:
        response = get_gtax_data(f'http://{gtax_instance}.intel.com/api/v1/clients?include_all_properties=true&full_info=true&per_page=10000')
        data = response.json()
        clients = data['data']
        with open('gtax_instance_clients.cache', 'w+b') as cache:
            pickle.dump(clients, cache) 
    return clients

def get_reserved(clients):
    reserved = []
    for client in clients:
        if client["is_reserved"]:
            reserved.append(client)
    return reserved

def get_property_value(properties, property_name):
    property_value = None
    for property in properties:
        if property["name"] == property_name:
            property_value = property["value"]
            break
    return property_value

gtax_clients = get_all_clients(True)

print(gtax_clients[1]["properties"][3]["property"]["name"])
print(get_property_value(gtax_clients[1]["properties"], "platform_name"))

#print(len(gtax_clients))


#print(len(get_reserved(gtax_clients)))

print(get_reserved(gtax_clients)[1].keys())



#print(f"'property:{property_string.replace(',','\t')}')

#for client in sorted(clients_list, key=itemgetter(0)):
#    print(f"{client[0]}:{client[1]}")


