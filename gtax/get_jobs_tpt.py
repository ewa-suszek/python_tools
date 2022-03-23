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

def main(dags, wf_user, status, dags_count, job_time_limit, offline_mode=False):
    start = time.time()
    dags_stream_list = get_dags_stream_list(dags)
    print(f'job time limit:{job_time_limit}')    
    gtax_sessions = dict()
    long_jobs_list = [add_title_row()]
    all_jobs_list = [add_title_row()]

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

    long_jobs_dict = dict()
    for job in jobs_dict:
        all_jobs_list.append(add_jobs_data_row(jobs_dict[job]))
        if jobs_dict[job]['duration_sec'] > job_time_limit:
            long_jobs_list.append(add_jobs_data_row(jobs_dict[job]))

    print(f'found {len(long_jobs_list)} long jobs')

    #list_2_html(all_jobs_list, f'all_jobs_list.html', sort_col=15, reverse=True)
    list_2_html(long_jobs_list, f'long_jobs_list.html', sort_col=8, reverse=True)
    list_2_html_table(long_jobs_list, f'long_jobs_table.html', sort_col=8, reverse=True)
  
    end = time.time()
    print(f'total time: {round(end-start,2)}s')
    # end main

def add_jobs_data_row(job_dict):
    data_row = list()
    data_row.append(html_link(job_dict['id'], link=f"https://{job_dict['instance']}.intel.com/#/jobs/{job_dict['id']}"))
    #data_row.append(html_link(job_dict['jobset_id'], link=f"https://{job_dict['instance']}.intel.com/#/jobsets/{job_dict['jobset_id']}"))
    #data_row.append(html_link(job_dict['jobset_session_id'], link=f"https://{job_dict['instance']}.intel.com/#/jobset_sessions/{job_dict['jobset_session_id']}"))
    data_row.append(html_link(job_dict['test_plan_id'], link=f"https://gta.intel.com/#/testplanning/plan/{job_dict['test_plan_id']}"))
    #for key in ['status', 'name', 'result', 'submission_type', 'submitted_date', 'assigned_date', 'started_date', 'dispatched_date', 'completed_date', 'post_processing_date', 'sync_artifacts_date', 'duration', 'plugin_runtime', 'cycle_type', 'tasks_aborted', 'tasks_blocked', 'tasks_canceled', 'tasks_failed', 'tasks_ignored', 'tasks_not_run', 'tasks_passed', 'tasks_running', 'tasks_timed_out', 'tasks_unsupported', 'tasks_total', 'instance']:
    for key in ['status', 'name', 'result', 'submission_type', 'submitted_date', 'completed_date', 'duration', 'cycle_type', 'tasks_total', 'instance']:
        if key in job_dict.keys():
            data_row.append(job_dict[key])
        else:
            data_row.append('')
    if 'client_name' in job_dict.keys() and 'client_id' in job_dict.keys():
        data_row.append(html_link(job_dict['client_name'], link=f"https://{job_dict['instance']}.intel.com/#/clients/{job_dict['client_id']}"))
    else:
        data_row.append(' ')
    if 'csq_link' in job_dict.keys():
        data_row.append(html_link('csq', link=job_dict['csq_link']))
    else:
        data_row.append('csq')
    return data_row

def add_title_row():
    #return ['id', 'jobset_id', 'jobset_session_id', 'test_plan_id', 'status', 'name', 'result', 'submission_type', 'submitted_date', 'assigned_date', 'started_date', 'dispatched_date', 'completed_date', 'post_processing_date', 'sync_artifacts_date', 'duration', 'plugin_runtime', 'cycle_type', 'tasks_aborted', 'tasks_blocked', 'tasks_canceled', 'tasks_failed', 'tasks_ignored', 'tasks_not_run', 'tasks_passed', 'tasks_running', 'tasks_timed_out', 'tasks_unsupported', 'tasks_total', 'instance', 'client', 'csq']
    return ['id', 'test_plan', 'status', 'name', 'result', 'submission_type', 'submitted_date', 'completed_date', 'duration', 'cycle_type', 'tasks_total', 'instance', 'client', 'csq']
    
def get_dags_stream_list(dags_text):
    dags_stream_list = list()
    dags = dags_text.split(',')
    for dag in dags:
        dags_stream_list.append(dag.split(':'))
    return dags_stream_list

def print_first_dict_item(data_dict):
    keys = list(data_dict.keys())
    print('')    
    print(f'{keys[0]}:{data_dict[keys[0]]}')
    print('')
    print(data_dict[keys[0]].keys())
    print('')

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

def list_2_html(list_data, file_name, sort_col=None, reverse=False, convert_sec=False):
    html_output = ''
    html_style = '<style>table {font-family:Verdana;font-size: 10px; border-collapse: collapse;} table, th, td {border: 1px solid black;} tr:nth-child(even) {background-color: #f2f2f2;}</style>'
    html_output = f'<!DOCTYPE html><html><head>{html_style}</head><body><div style="overflow-x:auto;"><table><tr>'
    for col_title in list_data[0]:
        html_output += f'<th>{col_title}</th>'
    html_output += '</tr>'
    data_only = list()
    for row in range(1, len(list_data)):
        data_only.append(list_data[row])
    if sort_col:
        data_only = sorted(data_only, key=itemgetter(sort_col), reverse=reverse)
    for row in range(len(data_only)):
        html_output += '<tr>'
        for col in range(len(data_only[row])):
            if convert_sec and sort_col == col:
                html_output += f'<td>{get_duration_time(data_only[row][col])}</td>'
            else:
                html_output += f'<td>{data_only[row][col]}</td>'
        html_output += '</tr>'
    html_output += '</table></div></body></html>'
    html_file = open(file_name, "w")
    html_file.write(html_output)
    html_file.close()
    print(f'Saved the output file:{file_name}')

def list_2_html_table(list_data, file_name, sort_col=None, reverse=False, convert_sec=False):
    html_output = ''
    html_output = '<table style="width:100%; border:1px solid black; border-collapse: collapse; font-family:verdana; font-size:12px;"><tr style="background-color:#70AD47;">'
    for col_title in list_data[0]:
        html_output += f'<th style="border:1px solid black;"><strong>{col_title}</strong></th>'
    html_output += '</tr>'
    data_only = list()
    for row in range(1, len(list_data)):
        data_only.append(list_data[row])
    if sort_col:
        data_only = sorted(data_only, key=itemgetter(sort_col), reverse=reverse)
    for row in range(len(data_only)):
        if row % 2 == 0:
            bg_color = '#E2EFD9'
        else:
            bg_color = '#FFFFFF'
        html_output += f'<tr style="background-color:{bg_color};">'
        for col in range(len(data_only[row])):
            if convert_sec and sort_col == col:
                html_output += f'<td style="border:1px solid black;">{get_duration_time(data_only[row][col])}</td>'
            else:
                html_output += f'<td style="border:1px solid black;">{data_only[row][col]}</td>'
        html_output += '</tr>'
    html_output += '</table></div></body></html>'
    html_file = open(file_name, "w")
    html_file.write(html_output)
    html_file.close()
    print(f'Saved the output file:{file_name}')

def html_link(link_text, link, custom_title=None):
    if custom_title:
        title_text = f'title="{custom_title}"'
    else:
        title_text = link
    return f'<a href="{link}" target="_blank" {title_text}>{link_text}</a>'

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
        #print(url)
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
        for key in ['id', 'jobset_id', 'jobset_session_id', 'status', 'name', 'result', 'submission_type', 'submitted_date', 'assigned_date', 'started_date', 'dispatched_date', 'completed_date', 'post_processing_date', 'sync_artifacts_date', 'duration', 'duration_sec', 'plugin_runtime', 'scheduler_account_name', 'dumps_produced', 'notes']:
            if key in job_data.keys():
                if key in ['duration', 'duration_sec']:
                    if isinstance(job_data[key], str):
                        job_dict.update({key:-1})
                    else:
                        job_dict.update({key:job_data[key]})
                else:
                    job_dict.update({key:job_data[key]})
        for key in ['dag_id', 'wf_id', 'cycle_type', 'test_plan_id']:
            job_dict.update({key:gtax_session[key]})
        if 'csq' in job_data.keys():
            csq = job_data['csq']['query']
            job_dict.update({'csq':csq, 'csq_link':get_csq_link(gtax_instance, csq)})
        if 'client' in job_data.keys():
            for key in ['name', 'id']:
                if key in job_data['client'].keys():
                    job_dict.update({f'client_{key}':job_data['client'][key]})
        if 'results_summary' in job_data.keys():
            for key in job_data['results_summary'].keys():
                job_dict.update({f'tasks_{key}':job_data['results_summary'][key]})
        job_dict.update({'instance': gtax_instance})
        session_jobs_dict.update({job_data['id']:job_dict})
    return session_jobs_dict

def get_duration_time(duration_sec):
    return str(timedelta(seconds=duration_sec))

def get_csq_link(gtax_instance, csq):
    csq_link = f'http://{gtax_instance}.intel.com/#/clients?csq='
    csq_html = urllib.parse.quote(csq).replace("%27","'").replace('%28','(').replace('%29',')')
    csq_link += f'{csq_html}&ensure_req_match=true'
    return csq_link

if __name__ == '__main__':
    user_pass = list()
    ap = argparse.ArgumentParser()
    ap.add_argument('-d', '-dags', default='CI_DAILY__gfx-driver__master__silicon:gfx-driver__master,CI_WEEKLY__gfx-driver__master__uber_gft:gfx-driver__master,CI_WEEKLY__gfx-driver__master__silicon-ehl:gfx-driver__master', help='coma seperated dag:stream exp: "CI_DAILY__gfx-driver__master__silicon:gfx-driver__master,CI_WEEKLY__gfx-driver__master__uber_gft:gfx-driver__master,CI_WEEKLY__gfx-driver__master__silicon-ehl:gfx-driver__master"', required=False)
    ap.add_argument('-u', '-user', default='sys_gtawf', help='wf cycle submiter (user idsid) note: use value "all" for any user', required=False)
    ap.add_argument('-s', '-status', default='COMPLETED', help='status filter values: [NEW, IN PROGRESS ,COMPLETED, ERROR, TIMEOUT, INCOMPLETE]', required=False)
    ap.add_argument('-c', '-count', default='1', help='number of cycles', required=False)
    ap.add_argument('-l', '-time_limit', default='21700', help='job time limit in sec.', required=False)
    ap.add_argument('-offline', action='store_true', default=False, help='offline mode', required=False)
    ap.add_argument('-login', default='', help='login', required=False)
    ap.add_argument('-password', default='', help='password', required=False)
    parsed = ap.parse_args()
    if len(parsed.login) > 1 and len(parsed.password) > 1:
        user_pass.append(parsed.login)
        user_pass.append(parsed.password)
    main(parsed.d, parsed.u, parsed.s, int(parsed.c), int(parsed.l), parsed.offline)
