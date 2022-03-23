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
import urllib.parse
import openpyxl
from openpyxl.styles import Font, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, PieChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList

def main(status, filename, branches=False, offline_mode=False):
    start = time.time()
    clients_limit = 5
    gtax_sessions = list()
    gtax_csq_list = list()
    missing_clients_list = [['client_group', 'csq_link', 'clients_count', 'wf_id', 'cycle_type', 'test_plan_id', 'gtax_instance', 'session_id', 'dag_id']]
    all_clients_list = [['client_group', 'csq_link', 'clients_count', 'wf_id', 'cycle_type', 'test_plan_id', 'gtax_instance', 'session_id', 'dag_id']]

    #MASTER
    gtax_sessions_cache = f'gtax_sessions_tmp.cache'
    if offline_mode and os.path.isfile(gtax_sessions_cache):
        with open(gtax_sessions_cache, 'rb') as cache:
            gtax_sessions = pickle.load(cache)
    else:
        update_gtax_session(gtax_sessions, get_cycles('CI_SMOKE__gfx-driver__master', 'gfx-driver__master', 'sys_gtawf', status, 1))
        update_gtax_session(gtax_sessions, get_cycles('CI_DAILY__gfx-driver__master__silicon', 'gfx-driver__master', 'sys_gtawf', status, 1))
        update_gtax_session(gtax_sessions, get_cycles('CI_WEEKLY__gfx-driver__master__uber_gft', 'gfx-driver__master', 'sys_gtawf', status, 1))
        update_gtax_session(gtax_sessions, get_cycles('CI_WEEKLY__gfx-driver__master__silicon-ehl', 'gfx-driver__master', 'sys_gtawf', status, 1))
        with open(gtax_sessions_cache, 'w+b') as cache:
            pickle.dump(gtax_sessions, cache) 

    for gtax_session in gtax_sessions:
        #print(f"{gtax_session['gtax_instance']} {gtax_session['session_id']}")
        csq_dict = get_csq_dict(get_jobs_dict_for_session_id(gtax_session['gtax_instance'], gtax_session['session_id'], offline_mode), gtax_session)
        gtax_csq_list.append(csq_dict)

    if not offline_mode:
        csq_api_calls = set()
        for csq_dict in gtax_csq_list:
            for csq in csq_dict:
                if csq_dict[csq]['client_group'] != 'blocked':
                    csq_api_calls.add(csq_dict[csq]['csq_api_link'])
        csq_total = len(csq_api_calls)
        print(f'unique csq to check: {csq_total}')
        csq_api_calls_dict = dict()
        csq_count = 0
        for api_call in csq_api_calls:
            csq_count += 1
            print(f'getting {csq_count}/{csq_total}', end='\r', flush=True)
            clients = get_clients_count(api_call)
            csq_api_calls_dict.update({api_call:clients})
        with open(f'csq_api_calls_dict_tmp.cache', 'w+b') as cache:
            pickle.dump(csq_api_calls_dict, cache)
        
    if offline_mode and os.path.isfile('all_clients_list_tmp.cache') and os.path.isfile('missing_clients_list.cache'):
        with open('all_clients_list_tmp.cache', 'rb') as cache:
            all_clients_list = pickle.load(cache)
        with open('missing_clients_list.cache', 'rb') as cache:
            missing_clients_list = pickle.load(cache)  
    else:
        for csq_dict in gtax_csq_list:
            for csq in csq_dict: 
                if csq_dict[csq]['client_group'] != 'blocked':
                    clients_count = csq_api_calls_dict[csq_dict[csq]['csq_api_link']]
                    all_clients_list.append([csq_dict[csq]['client_group'], html_link(csq_dict[csq]['csq_link'], 'csq_gtax_link', title=csq_dict[csq]['csq']), clients_count, csq_dict[csq]['gtax_session']['wf_id'], csq_dict[csq]['gtax_session']['cycle_type'], csq_dict[csq]['gtax_session']['test_plan_id'], csq_dict[csq]['gtax_session']['gtax_instance'], html_link(csq_dict[csq]['gtax_session']['gtax_link'], csq_dict[csq]['gtax_session']['session_id']), csq_dict[csq]['gtax_session']['dag_id']])
                    if clients_count < clients_limit:
                        csq_link = csq_dict[csq]['csq_link']
                        missing_clients_list.append([csq_dict[csq]['client_group'], html_link(csq_dict[csq]['csq_link'], 'csq_gtax_link', title=csq_dict[csq]['csq']), clients_count, csq_dict[csq]['gtax_session']['wf_id'], csq_dict[csq]['gtax_session']['cycle_type'], csq_dict[csq]['gtax_session']['test_plan_id'], csq_dict[csq]['gtax_session']['gtax_instance'], html_link(csq_dict[csq]['gtax_session']['gtax_link'], csq_dict[csq]['gtax_session']['session_id']), csq_dict[csq]['gtax_session']['dag_id']])
                    with open(f'all_clients_list_tmp.cache', 'w+b') as cache:
                        pickle.dump(all_clients_list, cache) 
                    with open(f'missing_clients_list.cache', 'w+b') as cache:
                        pickle.dump(missing_clients_list, cache) 
    
    #print(missing_clients_list)
    ts = get_filename_timestamp()
    list_2_html(all_clients_list, f'all_clients_list_{ts}.html')
    list_2_html(missing_clients_list, f'missing_clients_list_{ts}.html')
    end = time.time()
    print(f'total time: {round(end-start,2)}s')
    

    #BRANCHES
    if branches:
        gtax_sessions_branches = list()
        gtax_sessions_branches_cache = f'gtax_sessions_branches_tmp.cache'
        if offline_mode and os.path.isfile(gtax_sessions_branches_cache):
            with open(gtax_sessions_branches_cache, 'rb') as cache:
                gtax_sessions_branches = pickle.load(cache)
        else:
            ci_cycle_stat = list()
            ci_test_sessions_stat = list()
            update_gtax_session(gtax_sessions_branches, get_cycles('ON_DEMAND_TESTS__gfx-driver__comp_media__Smoke', 'gfx-driver__comp_media', None, status, 30))

            update_gtax_session(gtax_sessions_branches, get_cycles('CI_smoke__ci-neo_master', 'ci-neo_master', 'sys_gtawf', status, 30))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_SMOKE__gfx-driver__comp_glsl', 'gfx-driver__comp_glsl', 'sys_gtawf', status, 30))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_smoke__gfx-driver__comp_igc', 'gfx-driver__comp_igc', 'sys_gtawf', status, 30))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_SMOKE__open-linux-driver-ci-dev_igc', 'open-linux-driver-ci-dev_igc', 'sys_gtawf', status, 30))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_SMOKE__ci-neo_embargo', 'ci-neo_embargo', 'sys_gtawf', status, 30))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_SMOKE__gfx-driver__comp_ogl', 'gfx-driver__comp_ogl', 'sys_gtawf', status, 30))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_SMOKE__gfx-driver__comp_vulkan', 'gfx-driver__comp_vulkan', 'sys_gtawf', status, 30))

            update_gtax_session(gtax_sessions_branches, get_cycles('CI_daily__ci-neo_master', 'ci-neo_master', 'sys_gtawf', status, 20))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_daily__gfx-driver__comp_glsl', 'gfx-driver__comp_glsl', 'sys_gtawf', status, 20))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_daily__gfx-driver__comp_igc', 'gfx-driver__comp_igc', 'sys_gtawf', status, 20))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_DAILY__open-linux-driver-ci-dev_igc', 'open-linux-driver-ci-dev_igc', 'sys_gtawf', status, 20))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_daily__ci-neo_embargo', 'ci-neo_embargo', 'sys_gtawf', status, 20))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_daily__gfx-driver__comp_ogl', 'gfx-driver__comp_ogl', 'sys_gtawf', status, 20))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_DAILY__gfx-driver__comp_vulkan', 'gfx-driver__comp_vulkan', 'sys_gtawf', status, 20))
            
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_WEEKLY__ci-neo_master', 'ci-neo_master', 'sys_gtawf', status, 10))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_WEEKLY__ci-neo_embargo', 'ci-neo_embargo', 'sys_gtawf', status, 10))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_WEEKLY__gfx-driver__comp_ogl', 'gfx-driver__comp_ogl', 'sys_gtawf', status, 10))
            update_gtax_session(gtax_sessions_branches, get_cycles('CI_WEEKLY__gfx-driver__comp_vulkan', 'gfx-driver__comp_vulkan', 'sys_gtawf', status, 10))
            with open(gtax_sessions_branches_cache, 'w+b') as cache:
                pickle.dump(gtax_sessions_branches, cache) 
    return 0

def list_2_csv(list_data, file_name):
    with open(file_name, 'w', newline='') as f: 
        write = csv.writer(f) 
        write.writerows(list_data) 
    print(f'Saved the output file:{file_name}')

def list_2_html(list_data, file_name):
    html_output = ''
    html_style = '<style>table {font-family:Verdana;font-size: 10px; border-collapse: collapse;} table, th, td {border: 1px solid black;} tr:nth-child(even) {background-color: #f2f2f2;}</style>'
    html_output = f'<!DOCTYPE html><html><head>{html_style}</head><body><div style="overflow-x:auto;"><table><tr>'
    for col_title in list_data[0]:
        html_output += f'<th>{col_title}</th>'
    html_output += '</tr>'
    data_only = list()
    for row in range(1, len(list_data)):
        data_only.append(list_data[row])

    data_only = sorted(data_only, key=itemgetter(2))
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

def html_link(url, link_name, title=None):
    if title:
        title_text = f'title="{title}"'
    else:
        title_text = ''
    return f'<a href="{url}" target="_blank" {title_text}">{link_name}</a>'

def update_gtax_session(gtax_sessions, ci_cycles):
    gtax_sessions += get_gtax_sessions_from_ci_cycle(ci_cycles)
    return 0

def get_gtax_sessions_from_ci_cycle(ci_cycles):
    gtax_sessions_list = list()
    for cycle in ci_cycles:
        for session in cycle['test_sessions']:
            gtax_sessions_list.append({'dag_id':cycle['dag_id'], 'wf_id':session['id'], 'cycle_type':session['cycle_type'], 'test_plan_id':session['test_plan_id'], 'gtax_instance':session['remote_name'].replace('_','-'), 'session_id':session['external_id'], 'gtax_link':session['url']})
    return gtax_sessions_list

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

def post_gta_data(url, data):
    output = None
    headers = { 'Content-type': 'application/json' }
    response = requests.put(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    if response.status_code == 200:
        output = response
    else:
        print(response.status_code)
        print(response)
    return output

def get_gta_data(url):
    output = None
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    if response.status_code == 200:
        output = response
    else:
        print(response.status_code)
        print(response)
    return output

def get_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response.json()

def get_clients_count(csq_api_link):
    clients_count = 0
    clients = get_gtax_data(csq_api_link)['data']
    #get clients status and exclude in recovery offline unresponsive
    for client in clients:
        if client['status'] not in ['offline', 'unresponsive', 'in recovery'] and not client['is_reserved']:
            clients_count += 1
    return clients_count

def get_jobs_dict_for_session_id(gtax_instance, job_set_session_id, offline_mode=False):
    session_jobs_dict = dict()
    cache_file_name = f'gtax_{job_set_session_id}_tmp.cache'
    if offline_mode and os.path.isfile(cache_file_name):
        with open(cache_file_name, 'rb') as cache:
            session_jobs_dict = pickle.load(cache)
    else:
        print(f'getting data for job set session: {job_set_session_id}')
        url = f'http://{gtax_instance}.intel.com/api/v1/jobs?include_tasks=false&include_taskml=false&include_csq=true&full_info=false&jobset_session_ids={job_set_session_id}'
        #print(url)
        data = get_gtax_data(url)
        session_jobs_dict = get_session_jobs_dict(data['data'])
        with open(cache_file_name, 'w+b') as cache:
            pickle.dump(session_jobs_dict, cache) 
    return session_jobs_dict

def get_session_jobs_dict(session_jobs_data):
    session_jobs_dict = dict()
    for job_data in session_jobs_data:
        job_dict = dict()
        for key in ['id', 'status', 'name', 'result', 'submission_type', 'submitted_date', 'started_date', 'completed_date', 'duration', 'scheduler_account_name', 'dumps_produced']:
            job_dict.update({key:job_data[key]})
        for key in ['client', 'results_summary']:
            for sub_key in job_data[key].keys():
                key_name = f'{key}_{sub_key}'
                job_dict.update({key_name:job_data[key][sub_key]})
                if key_name == 'client_name':
                    job_dict.update({'client_group':get_client_group(job_data['client']['name'])})
        if 'csq' in job_data.keys():
            job_dict.update({'csq':job_data['csq']['query']})
        session_jobs_dict.update({job_data['id']:job_dict})
    return session_jobs_dict

def get_csq_dict(session_jobs_dict, gtax_session):
    csq_dict = dict()
    client_group_set = set()
    gtax_instance = gtax_session['gtax_instance']
    for job in session_jobs_dict:
        if session_jobs_dict[job]['result'] != 'blocked':
            client_group_set.add(session_jobs_dict[job]['client_group'])
    for group in client_group_set:
        csq_group_set = set()
        csq_group_jobs_list = list()
        for job in filer_report_data(session_jobs_dict, [['submission_type', 'init', 'match']]):
            if session_jobs_dict[job]['client_group'] == group:
                csq_group_set.add(session_jobs_dict[job]['csq'])
        index = 0
        for csq in csq_group_set:
            csq_dict.update({f'{group}_{index}':{'client_group':group, 'csq':csq, 'csq_link':get_csq_link(gtax_instance, csq), 'csq_api_link':get_csq_api_link(gtax_instance, csq), 'gtax_session':gtax_session}})
            index += 1
    csq_group_set = set()
    for job in filer_report_data(session_jobs_dict, [['result', 'blocked', 'match']]):
        csq_group_set.add(session_jobs_dict[job]['csq'])
    index = 0
    for csq in csq_group_set:
        csq_dict.update({f'blocked_{index}':{'client_group':'blocked', 'csq':csq, 'csq_link':get_csq_link(gtax_instance, csq), 'csq_api_link':get_csq_api_link(gtax_instance, csq), 'gtax_session':gtax_session}})
        index += 1
    csq_dict.update({})
    return csq_dict

def filer_report_data(report_data, condition_list, match_all=True):
    # format condition_list : [[condition_key1, condition_key1_value, condition_key1_func], [condition_key2, condition_key2_value, condition_key2_func]]
    # func: eql, n_eql, greater, greater_eql, less, less_eql, match, contain  
    report_data_filtered = dict()
    if match_all:
        for bug in report_data:
            condition_match = True
            for condition in condition_list:
                if check_condition(report_data[bug][condition[0]], condition[1], condition[2]) and condition_match == True:
                    condition_match = True
                else:
                    condition_match = False
            if condition_match == True:
                report_data_filtered.update({bug:report_data[bug]})
    else:
        for bug in report_data:
            condition_match = False
            for condition in condition_list:
                if check_condition(report_data[bug][condition[0]], condition[1], condition[2]):
                    condition_match = True
            if condition_match == True:
                report_data_filtered.update({bug:report_data[bug]})        
    return report_data_filtered

def check_condition(value, condition_value, condition_func):
    check = False
    if condition_func == 'eql':
        if float(value) == float(condition_value):
            check = True
    elif condition_func == 'n_eql':
        if float(value) != float(condition_value):
            check = True
    elif condition_func == 'greater_eql':
        if float(value) >= float(condition_value):
            check = True
    elif condition_func == 'greater':
        if float(value) > float(condition_value):
            check = True
    elif condition_func == 'less':
        if float(value) < float(condition_value):
            check = True
    elif condition_func == 'less_eql':
        if float(value) <= float(condition_value):
            check = True
    elif condition_func == 'match':
        if str(value) == str(condition_value):
            check = True
    elif condition_func == 'not_match':
        if str(value) != str(condition_value):
            check = True
    elif condition_func == 'contain':
        if str(value).find(str(condition_value)) >= 0:
            check = True
    else:
        check = False
    return check

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


def get_client_group(client_name):
    client_regex = re.compile(r'^.+?(-\d)') 
    client_group = client_name
    if client_regex.search(client_name):
        client_group = client_regex.search(client_name).group(0)[:-2]
    return client_group

def get_filename_timestamp():
    ts = str(datetime.now())
    ts = ts.replace(':', '_')
    return ts[5:-7]

if __name__ == '__main__':
    ts = get_filename_timestamp()
    filename = f'missing_clients_list_{ts}.xlsx'
    ap = argparse.ArgumentParser()
    ap.add_argument('-s', '-status', default='ALL', help='status filter', required=False)
    ap.add_argument('-b', '-branches', action='store_true', default=False, help='offline mode', required=False)
    ap.add_argument('-o', '-output', default=filename, help='output file name', required=False)
    ap.add_argument('-offline', action='store_true', default=False, help='offline mode', required=False)
    parsed = ap.parse_args()
    main(parsed.s, parsed.o, parsed.b, parsed.offline)
