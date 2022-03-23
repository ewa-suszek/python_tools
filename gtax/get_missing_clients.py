import sys
import math
import os.path
import argparse
import pickle
from datetime import datetime
from datetime import timedelta
from operator import itemgetter
import re
import time
import json
import csv 
import requests
from requests.auth import HTTPBasicAuth
import urllib.parse

def main(dags, wf_user, status, dags_count, clients_limit, use_cached_calls=False, offline_mode=False):
    start = time.time()
    dags_stream_list = get_dags_stream_list(dags)
    print(f'clients limit:{clients_limit}')    
    gtax_sessions = dict()
    missing_clients_list = [add_title_row()]
    limited_clients_list = [add_title_row()]
    all_clients_list = [add_title_row()]
    calls_to_skip = set()
    api_calls_to_skip_cache_file = 'api_calls_to_skip.cache'

    if use_cached_calls and os.path.isfile(api_calls_to_skip_cache_file):
        with open(api_calls_to_skip_cache_file, 'rb') as cache:
            calls_to_skip = pickle.load(cache)

    gtax_sessions_cache_file = f'gtax_sessions_tmp.cache'
    if offline_mode and os.path.isfile(gtax_sessions_cache_file):
        with open(gtax_sessions_cache_file, 'rb') as cache:
            gtax_sessions = pickle.load(cache)
    else:
        for dag_stream in dags_stream_list:
            if wf_user == 'all':
                wf_user = None
            update_gtax_session(gtax_sessions, get_cycles(dag_stream[0], dag_stream[1], wf_user, status, dags_count))
        with open(gtax_sessions_cache_file, 'w+b') as cache:
            pickle.dump(gtax_sessions, cache) 

    jobs_dict = dict()
    for gtax_session in gtax_sessions:
        jobs_dict.update(get_jobs_dict_for_session_id(gtax_sessions[gtax_session], gtax_session, offline_mode))

    #print_first_dict_item(jobs_dict)

    print(f'jobs to check: {len(jobs_dict)}')
    
    csq_api_calls = get_csq_api_calls_set(jobs_dict)
    csq_total = len(csq_api_calls) - len(calls_to_skip)
    print(f'unique csq to check: {csq_total}')

    if not offline_mode:
        csq_api_calls_clients_dict = dict()
        csq_count = 0
        for api_call in csq_api_calls:
            if api_call not in calls_to_skip:
                csq_count += 1
                #print(f'getting {csq_count}/{csq_total}', end='\r', flush=True)
                print(f'getting {csq_count}/{csq_total}')
                clients_dict = get_clients_count(api_call)
                csq_api_calls_clients_dict.update({api_call:clients_dict})
        with open(f'csq_api_calls_clients_dict_tmp.cache', 'w+b') as cache:
            pickle.dump(csq_api_calls_clients_dict, cache)
    else:
        with open('csq_api_calls_clients_dict_tmp.cache', 'rb') as cache:
            csq_api_calls_clients_dict = pickle.load(cache)
    
    
    #for api in csq_api_calls_clients_dict:
    #    print(csq_api_calls_clients_dict[api])
    

    for api_call in csq_api_calls_clients_dict:
        clients = csq_api_calls_clients_dict[api_call]['clients']
        all_clients_list.append(add_csq_data_row(api_call, csq_api_calls_clients_dict[api_call], jobs_dict))
        if clients == 0:
            missing_clients_list.append(add_csq_data_row(api_call, csq_api_calls_clients_dict[api_call], jobs_dict))
        if clients > 0 and clients < clients_limit:
            limited_clients_list.append(add_csq_data_row(api_call, csq_api_calls_clients_dict[api_call], jobs_dict))
        if clients > 20:
            calls_to_skip.add(api_call)

    with open(api_calls_to_skip_cache_file, 'w+b') as cache:
            pickle.dump(calls_to_skip, cache)

    list_2_html(all_clients_list, f'all_clients_list.html')
    list_2_html(missing_clients_list, f'missing_clients_list.html', sort_col=0)
    list_2_html_table(missing_clients_list, f'missing_clients_table.html', sort_col=0)
    list_2_html(limited_clients_list, f'limited_clients_list.html')
    list_2_html_table(limited_clients_list, f'limited_clients_table.html')
    count_2_txt(missing_clients_list, 'missing_clients_count.txt')
    count_2_txt(limited_clients_list, 'limited_clients_count.txt')
    end = time.time()
    print(f'total time: {round(end-start,2)}s')
    # end main

def add_csq_data_row(api_call, clients_dict, jobs_dict):
    clients_count = clients_dict['clients']
    data_row = list()
    data_row.append(print_html(get_job_key_set_for_csq('csq', api_call, jobs_dict), link=str(get_job_key_set_for_csq('csq_link', api_call, jobs_dict))[2:-2]))
    data_row.append(clients_count)
    data_row.append(add_clients_statuses_html(clients_dict))
    data_row.append(print_html(get_job_key_set_for_csq('jobset_session_id', api_call, jobs_dict), link=f'https://{get_instance_from_api_call(api_call)}.intel.com/#/jobset_sessions/@'))
    data_row.append(print_html(get_job_key_set_for_csq('jobset_id', api_call, jobs_dict), link=f'https://{get_instance_from_api_call(api_call)}.intel.com/#/jobsets/@'))
    #data_row.append(print_html(get_job_key_set_for_csq('id', api_call, jobs_dict), link=f'https://{get_instance_from_api_call(api_call)}.intel.com/#/jobs/@'))
    data_row.append(print_html(get_job_key_set_for_csq('cycle_type', api_call, jobs_dict)))
    data_row.append(print_html(get_job_key_set_for_csq('test_plan_id', api_call, jobs_dict), link=f'https://gta.intel.com/#/testplanning/plan/@'))
    data_row.append(print_html(get_job_key_set_for_csq('instance', api_call, jobs_dict)))
    return data_row

def add_title_row():
    title_row = list()
    title_row.append('csq')
    title_row.append('clients')
    title_row.append('clients statuses')
    title_row.append('jobset_sessions')
    title_row.append('jobsets')
    #title_row.append('jobs')
    title_row.append('cycle_types')
    title_row.append('test_plans')
    title_row.append('gtax_instance')
    return title_row

def add_clients_statuses_html(clients_dict):
    html_text = ''
    for status in sorted(clients_dict['status_stat'].keys()):
        html_text += f"{status}:{clients_dict['status_stat'][status]}"
        if status in clients_dict['reserved_status_stat'].keys():
            html_text += f"&nbsp;<strong>({clients_dict['reserved_status_stat'][status]})</strong>"
        html_text += "</br>"
    if clients_dict['reserved'] > 0:
        html_text += f"<strong>total reserved:{clients_dict['reserved']}</strong>"
    return html_text

def print_html(set_to_print, link=None):
    html_text = ''
    count = 0
    for item in set_to_print:
        if link:
            url = link.replace('@',str(item))
            html_text += html_link(url, str(item), title=url)
        else:
            html_text += str(item)
        count += 1
        if count < len(set_to_print):
            html_text += '</br>'
    return html_text

def get_dags_stream_list(dags_text):
    dags_stream_list = list()
    dags = dags_text.split(',')
    for dag in dags:
        dags_stream_list.append(dag.split(':'))
    return dags_stream_list

def print_first_dict_item(data_dict):
    keys = list(data_dict.keys())
    print(data_dict[keys[0]])

def list_2_csv(list_data, file_name):
    with open(file_name, 'w', newline='') as f: 
        write = csv.writer(f) 
        write.writerows(list_data) 
    print(f'Saved the output file:{file_name}')

def count_2_txt(list_data, file_name, header=True):
    list_count = len(list_data)
    if header:
        list_count -= 1
    with open(file_name, 'w', newline='') as f: 
        f.write(str(list_count)) 
    print(f'Saved the output file:{file_name}')

def list_2_txt(list_data, file_name):
    with open(file_name, 'w', newline='') as f: 
        f.write(str(list_data))
    print(f'Saved the output file:{file_name}')
    

def list_2_html(list_data, file_name, sort_col=1):
    html_output = ''
    html_style = '<style>table {font-family:Verdana;font-size: 10px; border-collapse: collapse;} table, th, td {border: 1px solid black;} tr:nth-child(even) {background-color: #f2f2f2;}</style>'
    html_output = f'<!DOCTYPE html><html><head>{html_style}</head><body><div style="overflow-x:auto;"><table><tr>'
    for col_title in list_data[0]:
        html_output += f'<th>{col_title}</th>'
    html_output += '</tr>'
    data_only = list()
    for row in range(1, len(list_data)):
        data_only.append(list_data[row])

    data_only = sorted(data_only, key=itemgetter(sort_col))
    for row in range(len(data_only)):
        html_output += '<tr>'
        for col_data in data_only[row]:
            html_output += f'<td>{col_data}</td>'
        html_output += '</tr>'
    html_output += '</table></div></body></html>'
    html_file = open(file_name, "w")
    html_file.write(html_output)
    html_file.close()
    print(f'Saved the output file:{file_name}')


def list_2_html_table(list_data, file_name, sort_col=1):
    html_output = ''
    html_output = '<table style="width:100%; border:1px solid black; border-collapse: collapse; font-family:verdana; font-size:12px;"><tr style="background-color:#70AD47;">'
    for col_title in list_data[0]:
        html_output += f'<th style="border:1px solid black;"><strong>{col_title}</strong></th>'
    html_output += '</tr>'
    data_only = list()
    for row in range(1, len(list_data)):
        data_only.append(list_data[row])

    data_only = sorted(data_only, key=itemgetter(sort_col))
    for row in range(len(data_only)):
        if row % 2 == 0:
            bg_color = '#E2EFD9'
        else:
            bg_color = '#FFFFFF'
        html_output += f'<tr style="background-color:{bg_color};">'
        for col_data in data_only[row]:
            html_output += f'<td style="border:1px solid black;">{col_data}</td>'
        html_output += '</tr>'
    html_output += '</table></div></body></html>'
    html_file = open(file_name, "w")
    html_file.write(html_output)
    html_file.close()
    print(f'Saved the output file:{file_name}')

def html_link(url, link_name, title=None):
    if title:
        title_text = f'title="{title}"'
    else:
        title_text = ''
    return f'<a href="{url}" target="_blank" {title_text}>{link_name}</a>'

def update_gtax_session(gtax_sessions, ci_cycles):
    gtax_sessions.update(get_gtax_sessions_from_ci_cycle(ci_cycles))
    return 0

def get_gtax_sessions_from_ci_cycle(ci_cycles):
    gtax_sessions_dict = dict()
    for cycle in ci_cycles:
        for session in cycle['test_sessions']:
            gtax_sessions_dict.update({session['external_id']:{'dag_id':cycle['dag_id'], 'wf_id':session['id'], 'cycle_type':session['cycle_type'], 'test_plan_id':session['test_plan_id'], 'gtax_instance':session['remote_name'].replace('_','-'), 'session_id':session['external_id'], 'gtax_link':session['url']}})
    return gtax_sessions_dict

def get_cycles(dag_id, stream, submitter=None, status=None, count=10):
    url = f'http://gta.intel.com/api/workflow/v2/test_runs_dashboard?page=1&count={count}&filter%5Bdag_id%5D={dag_id}'
    if submitter:
        url += f'&filter%5Bsubmitter%5D={submitter}'
    if stream:
        url += f'&filter%5Bstream%5D={stream}'
    if status in ['NEW', 'IN PROGRESS' ,'COMPLETED', 'ERROR', 'TIMEOUT', 'INCOMPLETE']:
        url += f'&filter%5Bstatus%5D={status}'
    url += '&sorting%5Bid%5D=desc&filter%5Bexact_dag_id%5D=true'
    print(f'geting cycles: {dag_id} {stream} status:{status}')
    #print(url)
    response = get_gta_data(url)
    cycles = response.json()
    return cycles['items']

def get_dag_stream(dag):
    stream = None
    stream_position = dag.find('__')
    if stream_position > 0:
        stream = dag[stream_position:]
    return stream

def get_gta_data(url):
    global user_pass
    output = None
    headers = { 'Content-type': 'application/json' }
    if len(user_pass) == 2:
        response = requests.get(url, auth=HTTPBasicAuth(user_pass[0], user_pass[1]), headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    else:
        response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    if response.status_code == 200:
        output = response
    else:
        print(response.status_code)
        print(response)
    return output

def get_gtax_data(url):
    global user_pass
    headers = { 'Content-type': 'application/json' }
    if len(user_pass) == 2:
        response = requests.get(url, auth=HTTPBasicAuth(user_pass[0], user_pass[1]), headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' }, verify=False)
    else:
        response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response.json()


def get_clients_count(csq_api_link):
    clients_dict = dict()
    clients_status_list = list()
    reserved_clients_status_list = list()
    clients_count = 0
    clients_total_count = 0
    clients_reserved_count = 0
    clients = get_gtax_data(csq_api_link)['data']
    #get clients status and exclude in recovery offline unresponsive
    for client in clients:
        clients_total_count += 1
        clients_status_list.append(client['status'])
        if client['status'] not in ['offline', 'unresponsive', 'in recovery', 'needs recovery'] and not client['is_reserved']:
            clients_count += 1
        if client['is_reserved']:
            clients_reserved_count += 1
            reserved_clients_status_list.append(client['status'])
    clients_dict.update({'clients':clients_count})
    clients_dict.update({'reserved':clients_reserved_count})
    clients_dict.update({'total':clients_total_count})
    clients_dict.update({'status_stat':get_status_stat(clients_status_list)})
    clients_dict.update({'reserved_status_stat':get_status_stat(reserved_clients_status_list)})
    return clients_dict

def get_status_stat(clients_status_list):
    clients_status_stat = dict()
    status_set = set()
    for status in clients_status_list:
        status_set.add(status)
    for status in status_set:
        clients_status_stat.update({status.replace(' ', '&nbsp;'):clients_status_list.count(status)})
    return clients_status_stat


def get_jobs_dict_for_session_id(gtax_session, job_set_session_id, offline_mode=False):
    gtax_instance = gtax_session['gtax_instance']
    session_jobs_dict = dict()
    cache_file_name = f'gtax_{job_set_session_id}_tmp.cache'
    if offline_mode and os.path.isfile(cache_file_name):
        with open(cache_file_name, 'rb') as cache:
            session_jobs_dict = pickle.load(cache)
    else:
        print(f'getting data for job set session: {job_set_session_id}')
        url = f'http://{gtax_instance}.intel.com/api/v1/jobs?include_tasks=false&include_taskml=false&include_csq=true&full_info=false&jobset_session_ids={job_set_session_id}'
        data = get_gtax_data(url)
        session_jobs_dict = get_session_jobs_dict(data['data'], gtax_session)
        with open(cache_file_name, 'w+b') as cache:
            pickle.dump(session_jobs_dict, cache) 
    return session_jobs_dict

def get_session_jobs_dict(session_jobs_data, gtax_session):
    gtax_instance = gtax_session['gtax_instance']
    session_jobs_dict = dict()
    for job_data in session_jobs_data:
        job_dict = dict()
        for key in ['id', 'jobset_id', 'jobset_session_id', 'status', 'name', 'result', 'submission_type', 'submitted_date', 'started_date', 'completed_date', 'duration', 'scheduler_account_name', 'dumps_produced']:
            job_dict.update({key:job_data[key]})
        for key in ['dag_id', 'wf_id', 'cycle_type', 'test_plan_id']:
            job_dict.update({key:gtax_session[key]})
        if 'csq' in job_data.keys():
            csq = job_data['csq']['query']
            job_dict.update({'csq':csq, 'csq_link':get_csq_link(gtax_instance, csq), 'csq_api_link':get_csq_api_link(gtax_instance, csq)})
        job_dict.update({'instance': gtax_instance})
        session_jobs_dict.update({job_data['id']:job_dict})
    return session_jobs_dict

# for job_key 'id', 'jobset_id', 'jobset_session_id'
def get_job_key_set_for_csq(job_key, csq_api_link, session_jobs_dict):
    jobs_ids_set = set()
    for job in session_jobs_dict:
        if 'csq_api_link' in session_jobs_dict[job].keys():
            if session_jobs_dict[job]['csq_api_link'] == csq_api_link:
                jobs_ids_set.add(session_jobs_dict[job][job_key])
    return jobs_ids_set

def get_csq_api_calls_set(jobs_dict):
    csq_set = set()
    for job in jobs_dict:
        if jobs_dict[job]['result'] != 'blocked' and jobs_dict[job]['submission_type'] == 'init':
                if 'csq' in jobs_dict[job].keys():
                    csq_set.add(get_csq_api_link(jobs_dict[job]['instance'], jobs_dict[job]['csq']))
                else:
                    print(f'job with no csq:{jobs_dict[job]}')
    return csq_set

def get_csq_link(gtax_instance, csq):
    csq_link = f'http://{gtax_instance}.intel.com/#/clients?csq='
    csq_html = urllib.parse.quote(csq).replace("%27","'").replace('%28','(').replace('%29',')')
    csq_link += f'{csq_html}&ensure_req_match=true'
    return csq_link

def get_csq_api_link(gtax_instance, csq):
    csq_link = f'http://{gtax_instance}.intel.com/api/v1/clients?csq='
    csq_html = urllib.parse.quote(csq).replace("%27","'").replace('%28','(').replace('%29',')')
    csq_link += f'{csq_html}&ensure_req_match=true'
    return csq_link

def get_instance_from_api_call(api_call):
    intel_position = api_call.find('.intel.com')
    return api_call[7:intel_position]

def get_client_group(client_name):
    client_regex = re.compile(r'^.+?(-\d)') 
    client_group = client_name
    if client_regex.search(client_name):
        client_group = client_regex.search(client_name).group(0)[:-2]
    return client_group

if __name__ == '__main__':
    user_pass = list()
    ap = argparse.ArgumentParser()
    ap.add_argument('-d', '-dags', default='CI_DAILY__gfx-driver__master__silicon:gfx-driver__master,CI_WEEKLY__gfx-driver__master__uber_gft:gfx-driver__master,CI_WEEKLY__gfx-driver__master__silicon-ehl:gfx-driver__master', help='coma seperated dag:stream exp: "CI_DAILY__gfx-driver__master__silicon:gfx-driver__master,CI_WEEKLY__gfx-driver__master__uber_gft:gfx-driver__master,CI_WEEKLY__gfx-driver__master__silicon-ehl:gfx-driver__master"', required=False)
    ap.add_argument('-u', '-user', default='sys_gtawf', help='wf cycle submiter (user idsid) note: use value "all" for any user', required=False)
    ap.add_argument('-s', '-status', default='COMPLETED', help='status filter values: [NEW, IN PROGRESS ,COMPLETED, ERROR, TIMEOUT, INCOMPLETE]', required=False)
    ap.add_argument('-c', '-count', default='1', help='number of cycles', required=False)
    ap.add_argument('-l', '-clients_limit', default='5', help='clients limit', required=False)
    ap.add_argument('-use_cache', action='store_true', default=False, help='use cached calls', required=False)
    ap.add_argument('-offline', action='store_true', default=False, help='offline mode', required=False)
    ap.add_argument('-login', default='', help='login', required=False)
    ap.add_argument('-password', default='', help='password', required=False)
    parsed = ap.parse_args()
    if len(parsed.login) > 1 and len(parsed.password) > 1:
        user_pass.append(parsed.login)
        user_pass.append(parsed.password)
    main(parsed.d, parsed.u, parsed.s, int(parsed.c), int(parsed.l), parsed.use_cache, parsed.offline)
