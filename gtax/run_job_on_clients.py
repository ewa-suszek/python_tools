import sys
import os
import argparse
import json
import requests
from datetime import datetime

def main(gtax_instance, client_search_string, job_name, file_name, is_csq, is_list_mode, filter_offline, action=None):
    jobset_session_ids = list()
    clients_dict = get_clients(gtax_instance, client_search_string, is_csq, filter_offline) 
    print(f'clients found: {len(clients_dict)} {offline_msg(filter_offline)}')
    for client in clients_dict:
        print(f'requesting job name {job_name} from {file_name} on {client["name"]} ({client["id"]}) [{client["status"]}]')
        if is_list_mode:
            print('list mode - no changes on client!')
        else:
            session_id = run_gtax_job(gtax_instance, client["id"], job_name, get_job_data(file_name))
            if session_id:
                print('successful')
                jobset_session_ids.append(str(session_id))
            else:
                print('false!! not set!!')
    for session_id in jobset_session_ids:
        print(f'http://{gtax_instance}.intel.com/#/jobset_sessions/{session_id}')
    save_check_results_bat(gtax_instance, job_name, jobset_session_ids, action)
    return 0
    
def save_check_results_bat(gtax_instance, job_name, jobset_session_ids, action):
    if action:
        action_string = f'-a "{action}"'
    else:
        action_string = ''
    if len(jobset_session_ids) > 0:
        app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        result_check_path = os.path.join(app_path, 'result_check')
        jobs_list_string = ','.join(jobset_session_ids)
        file_name = os.path.join(result_check_path, f'{job_name}-{get_filename_timestamp()}.bat')
        if not os.path.exists(result_check_path):
            os.makedirs(result_check_path)
        with open(file_name, 'w') as outfile:
            outfile.write('@echo off\r\n')
            outfile.write(f'..\get_jobs_results.exe -s "{jobs_list_string}" -i {gtax_instance} -html {action_string}\r\n')
            outfile.write('pause\r\n')
        print(f'check result bat saved: {file_name}')
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
            url = f'http://{gtax_instance}.intel.com/api/v1/clients?csq={client_search_string}&include_all_properties=false&full_info=false&order_by=name'
        else:
            url = f'http://{gtax_instance}.intel.com/api/v1/clients?include_all_properties=false&full_info=false&name={client_search_string}&order_by=name'
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

def run_gtax_job(gtax_instance, client_id, job_name, job_data):
    data = '{'
    data += f'"job_name": "{job_name}",'
    data += f'"job_data": {job_data},'
    data += f'"client_id": {client_id},'
    data += f'"submitter": "{os.getlogin()}"'
    data += '}'
    response = post_gtax_data(f'http://{gtax_instance}.intel.com/api/v1/jobs', data)
    if response.status_code == 200:
        response_data = response.json()
        jobset_session_id = response_data['jobset_session_id']
    else:
        jobset_session_id = None
        print(response)
        print(response.text)
    return jobset_session_id

def get_job_data(file_name):
    with open(file_name, 'r') as f:
        task_ml = f.read()
    return json.dumps(task_ml)

def post_gtax_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.post(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def get_gtax_data(url):
    gatx_data = None
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    if response.status_code == 200:
        gatx_data = response.json()
    else:
        print(url)
        print(response)
        print(response.text)
    return gatx_data

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

def get_filename_timestamp():
    ts = str(datetime.now())
    ts = ts.replace(':', '_').replace(' ', '_')
    return ts[0:-7]

if __name__ == '__main__':
    usage_msg = '''run_job_on_clients.exe -s GK-RKL%% -n job_name -f job_taskml_file.taskML
       run_job_on_clients.exe -csq ('pool' = 'CI_RKL') -n job_name -f job_taskml_file.taskML -offline skip
       run_job_on_clients.exe -csq ('platform' = 'Rocket Lake') -i gtax-gcmxd-fm -n job_name -f job_taskml_file.taskML
       run_job_on_clients.exe -h'''
    ap = argparse.ArgumentParser(usage=usage_msg)
    ap.add_argument('-i', '-instance', default='gtax-igk', help='gtax instance:[gtax-igk, gtax-gcmxd-fm, gtax-ril-fm]', required=False)
    ap.add_argument('-s', '-search', help="search clients by name: GK-RKL%%", required=False)
    ap.add_argument('-csq', help="csq query: ('pool' = 'CI_RKL') AND ('platform' = 'Rocket Lake')", required=False)
    ap.add_argument('-n', '-name', help='job name', required=True)
    ap.add_argument('-f', '-file', help='taskML file', required=True)
    ap.add_argument('-offline', default=False, const='all', nargs='?', choices=['skip', 'only'],help='offline clients skip or only', required=False)
    ap.add_argument('-l', '-list', action='store_true', default=False, help='list only mode (no changes on clients)', required=False)
    ap.add_argument('-a', '-action',  default=None, help="action based on results exp: udp#name:udp_name&p_value:pass_value&f_value:fail_value&req_failed:true - will be added to result check bat file")
    parsed = ap.parse_args()
    log_script_call()
    if not (parsed.s or parsed.csq):
        ap.error('\nNo params! Use -s or -csq')
    else:
        if parsed.s:
            main(parsed.i, parsed.s, parsed.n, parsed.f, False, parsed.l, parsed.offline, action=parsed.a)
        if parsed.csq:
            main(parsed.i, parsed.csq, parsed.n, parsed.f, True, parsed.l, parsed.offline, action=parsed.a)
