import json
import requests
#from deepdiff import DeepDiff
from jsondiff import diff
from json2html import *

#http://gtax-gcmxd-fm.intel.com/api/v1/

gtax_instance = 'gtax-gcmxd-fm'
client_1_name = 'FM-RKS-071'
client_2_name = 'FM-RKS-050'
html_style = '<style>table {font-family:Verdana;font-size: 10px; border-collapse: collapse;}table, th, td {border: 1px solid black;}</style>'
html_output = f'<!DOCTYPE html><html><head>{html_style}</head><body><table style="width:100%"><tr><th>property</th><th>{client_1_name}</th><th>{client_2_name}</th></tr>'

def get_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def get_client_id(client_name):
    response = get_gtax_data(f'http://{gtax_instance}.intel.com/api/v1/clients?name={client_name}&order_by=name')
    clients = response.json()
    return clients['data'][0]['id']

def get_client_properties(client_id):
    response = get_gtax_data(f'http://{gtax_instance}.intel.com/api/v1/clients/{client_id}/properties')
    properties = response.json()
    return properties

client_1_properties = get_client_properties(get_client_id(client_1_name))
client_2_properties = get_client_properties(get_client_id(client_2_name))

all_keys_set = set()

for key in client_1_properties['auto_detected'].keys():
     all_keys_set.add(key)

for key in client_2_properties['auto_detected'].keys():
     all_keys_set.add(key)

for key in all_keys_set:
    if key in client_1_properties['auto_detected'].keys():
        client_1_value = client_1_properties['auto_detected'][key]
    else:
        client_1_value = None
    if key in client_2_properties['auto_detected'].keys():
        client_2_value = client_2_properties['auto_detected'][key]
    else:
        client_2_value = None
    if client_1_value != client_2_value:
        html_output += f"<tr><td>{key}</td><td>{client_1_value}</td><td>{client_2_value}</td></tr>"

all_keys_set = set()

for key in client_1_properties['user_defined'].keys():
     all_keys_set.add(key)

for key in client_2_properties['user_defined'].keys():
     all_keys_set.add(key)

for key in all_keys_set:
    if key in client_1_properties['user_defined'].keys():
        client_1_value = client_1_properties['user_defined'][key]
    else:
        client_1_value = None
    if key in client_2_properties['user_defined'].keys():
        client_2_value = client_2_properties['user_defined'][key]
    else:
        client_2_value = None
    if client_1_value != client_2_value:
        html_output += f"<tr><td>{key}</td><td>{client_1_value}</td><td>{client_2_value}</td></tr>"

html_output += "</table></body></html>"

html_file = open("output.html", "w")
html_file.write(html_output)
html_file.close()
