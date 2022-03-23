import json
import requests
import sys
import argparse

#http://gtax-gcmxd-fm.intel.com/api/v1/


def get_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def get_client_id(gtax_instance, client_name):
    client_id = None
    response = get_gtax_data(f'http://{gtax_instance}.intel.com/api/v1/clients?name={client_name}&order_by=name')
    if response.status_code == 200:
        clients = response.json()
        if len(clients['data']) > 0:
            if 'id' in clients['data'][0].keys():
                client_id = clients['data'][0]['id']
        else:
            print(f'no client id found for name {client_name}')
    else:
        print(response)
    return client_id

def get_client_properties(gtax_instance, client_id):
    properties = None
    if client_id:
        url = f'http://{gtax_instance}.intel.com/api/v1/clients/{client_id}/properties'
        print(f'getting data for client id {client_id} from {url}')
        response = get_gtax_data(url)
        if response.status_code == 200:
            properties = response.json()
            properties.update({'gtax_instance':gtax_instance})
        else:
            print(response)
    return properties

def get_clients_properties(clients_list):
    clients_properties_list = []
    for client in clients_list:
        if len(client.split(':')) > 1:
            gtax_instance = client.split(':')[0]
            client_name = client.split(':')[1]
            client_id = get_client_id(gtax_instance, client_name)
            if client_id:
                clients_properties_list.append(get_client_properties(gtax_instance, client_id))
        else:
            print(f'wrong client format for client: {client} use instance:client_name!')
    return clients_properties_list

def get_all_clients_keys(client_properties_list, main_key):
    keys_set = set()
    for client_properties in client_properties_list:
        if client_properties[main_key]:
            for key in client_properties[main_key].keys():
                keys_set.add(key)
    return keys_set

def print_keys_to_html(key, clients_property_values):
    html_text = f'<tr><td style="font-weight: bold;">{key}</td>'
    for client_property_value in clients_property_values:
        html_text += f'<td>{client_property_value}</td>'
    html_text += f'</tr>'
    return html_text

def html_table_seperator(title, colspan):
    return f'<tr><td colspan="{colspan}" style="text-align:center; font-weight: bold; background-color: #BBBBBB;">{title}</td></tr>'

def check_all_not_equal(clients_property_values):
    values_set = set()
    for client_property_value in clients_property_values:
        values_set.add(client_property_value)
    if len(values_set) == 1:
        all_not_equal = False
    else:
        all_not_equal = True
    return all_not_equal

def html_output_keys(client_properties_list, main_key, keys_set, diff_mode='diff'):
    html_output = ''
    for key in sorted(keys_set):
        clients_property_values = []
        for client_properties in client_properties_list:
            if key in client_properties[main_key].keys():
                clients_property_values.append(client_properties[main_key][key])
            else:
                clients_property_values.append(None)
        if diff_mode == 'diff' or diff_mode == 'match':
            if check_all_not_equal(clients_property_values) and diff_mode == 'diff':
                html_output += print_keys_to_html(key, clients_property_values)
            if not check_all_not_equal(clients_property_values) and diff_mode == 'match':
                html_output += print_keys_to_html(key, clients_property_values)
        else:
            html_output += print_keys_to_html(key, clients_property_values)
    return html_output

def main(gtax_instance, clients_string, diff_mode, output_file_name):
    clients_list = list()
    
    if clients_string.find(':') > 0:
        # if client list with instance seperated by :
        # gtax-shared-fm:FM-ATS-020,FM-ATS-021;gtax-sc:SC-ATS-132,SC-ATS-073
        clients_instance_list = clients_string.split(';')
        for client_instance in clients_instance_list:
            instance = client_instance.split(':')[0]
            clients = client_instance.split(':')[1]
            for client in clients.split(','):
                clients_list.append(f'{instance}:{client}')
    else:
        # assume all clients on the same instance
        clients_no_instance_list = clients_string.split(',')
        for clients_no_instance in clients_no_instance_list:
            clients_list.append(f'{gtax_instance}:{clients_no_instance}')

    print(f'clients to compare: {clients_list}')
    clients_properties_list = get_clients_properties(clients_list)
    all_auto_keys_set = get_all_clients_keys(clients_properties_list, 'auto_detected')
    all_user_keys_set = get_all_clients_keys(clients_properties_list, 'user_defined')
    html_output = ''
    colspan = len(clients_list)+1
    html_style = '<style>table {font-family:Verdana;font-size: 10px; border-collapse: collapse; width:100%;} table, th, td {border: 1px solid black;} tr:nth-child(even) {background-color: #f2f2f2;}</style>'
    html_output = f'<!DOCTYPE html><html><head>{html_style}</head><body><div style="overflow-x:auto;"><table><tr><th>property</th>'

    for client in clients_properties_list:
        html_output += f"<th><a href='http://{client['gtax_instance']}.intel.com/#/clients/{client['auto_detected']['client_id']}?tab=properties' target='_blank'>{client['auto_detected']['client_name']}</a></th>"
    html_output += f'</tr>'
    html_output += html_table_seperator('auto_detected', colspan)
    html_output += html_output_keys(clients_properties_list, 'auto_detected', all_auto_keys_set, diff_mode=diff_mode)
    html_output += html_table_seperator('user_defined', colspan)
    html_output += html_output_keys(clients_properties_list, 'user_defined', all_user_keys_set, diff_mode=diff_mode)
    html_output += '</table></div></body></html>'

    html_file = open(output_file_name, "w")
    html_file.write(html_output)
    html_file.close()

    return 0

if __name__ == '__main__':
    usage_msg = '''clients_compare.exe -c "GK-RKL-S-005,GK-RKL-S-001,GK-RKL-S-006"
       clients_compare.exe -c "FM-KLT-023,FM-KLT-025" -i gtax-gcmxd-fm
       clients_compare.exe -c "FM-KLT-023,FM-KLT-025" -i gtax-gcmxd-fm -m match
       clients_compare.exe -c "FM-KLT-023,FM-KLT-025" -i gtax-gcmxd-fm -m all
       clients_compare.exe -c "FM-KLT-023,FM-KLT-025" -i gtax-gcmxd-fm -o my_output_file_name.html
       optional with instance:
       ; - instance with clients separator
       : - instance and clients separator
       instance1:client1_name,client2_name;instance2:client3_name,client4_name
       clients_compare.exe -c "gtax-shared-fm:FM-ATS-020,FM-ATS-021;gtax-sc:SC-ATS-132,SC-ATS-073"'''
    ap = argparse.ArgumentParser(usage=usage_msg)
    ap.add_argument('-i', '-instance', default='gtax-igk', help='gtax instance:[gtax-igk, gtax-gcmxd-fm]', required=False)
    ap.add_argument('-c', '-clients', help='clients list (optional with instance): "gtax-shared-fm:FM-ATS-020,FM-ATS-021;gtax-sc:SC-ATS-132,SC-ATS-073"', required=True)
    ap.add_argument('-m', '-mode', default='diff', choices=['diff', 'match', 'all'], help='diff mode: [diff, match, all]', required=False)
    ap.add_argument('-o', '-output', default='output.html', help='output file name: output.html', required=False)
    parsed = ap.parse_args()
    #print(parsed)
    #gtax-shared-fm:FM-ATS-020,gtax-sc:SC-ATS-132
    if parsed.c:
        main(parsed.i, parsed.c, parsed.m, parsed.o)
