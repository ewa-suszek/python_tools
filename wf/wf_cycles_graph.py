import sys
import math
import os.path
import argparse
import pickle
from datetime import datetime
from datetime import timedelta
from operator import itemgetter
import time
import json
import requests
import plotly.express as px
import plotly.figure_factory as ff
import pandas as pd

# need orca to work
# https://plotly.com/python/orca-management/
# https://github.com/plotly/orca/releases




def main(status, branches=False, offline_mode=False):
    #MASTER
    file_name = 'CI_CYCLES_MASTER.html'

    with open(file_name, 'w') as f:
        f.write('<html><head><meta charset="utf-8" /></head><body>')
    
    add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_SMOKE__gfx-driver__master', 'gfx-driver__master', 'sys_gtawf', status, 30)), 'CI_SMOKE__gfx-driver__master', plot_height=1000, bars_colors='#888888')
    
    ci_cycles = get_cycles('CI_DAILY__gfx-driver__master__silicon', 'gfx-driver__master', 'sys_gtawf', status, 20)
    add_plot(file_name, get_ci_cycle_stat(ci_cycles), 'CI_DAILY__gfx-driver__master__silicon', plot_height=1000, bars_colors='#ff0000')
    add_plot(file_name, get_ci_cycle_session_stat(ci_cycles), 'SESSIONS CI_DAILY__gfx-driver__master__silicon', plot_height=5000, bars_colors='#0000bb', task_key='test_plan_name_and_build')

    add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_WEEKLY__gfx-driver__master__uber_gft', 'gfx-driver__master', 'sys_gtawf', status, 10)), 'CI_WEEKLY__gfx-driver__master__uber_gft', plot_height=1000, bars_colors='#0000ff')
    add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_WEEKLY__gfx-driver__master__silicon-ehl', 'gfx-driver__master', 'sys_gtawf', status, 10)), 'CI_WEEKLY__gfx-driver__master__silicon-ehl', plot_height=1000, bars_colors='#0000ff')

    with open(file_name, 'a') as f:
        f.write('</body></html>')
    print(f'Saved the output file:{file_name}')

    #BRANCHES
    if branches:
  
        file_name = 'CI_CYCLES_BRANCHES.html'
    
        with open(file_name, 'w') as f:
            f.write('<html><head><meta charset="utf-8" /></head><body>')

        add_plot(file_name, get_ci_cycle_stat(get_cycles('ON_DEMAND_TESTS__gfx-driver__comp_media__Smoke', 'gfx-driver__comp_media', None, status, 30)), 'ON_DEMAND_TESTS__gfx-driver__comp_media__Smoke', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_smoke__ci-neo_master', 'ci-neo_master', 'sys_gtawf', status, 30)), 'CI_smoke__ci-neo_master', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_SMOKE__gfx-driver__comp_glsl', 'gfx-driver__comp_glsl', 'sys_gtawf', status, 30)), 'CI_SMOKE__gfx-driver__comp_glsl', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_smoke__gfx-driver__comp_igc', 'gfx-driver__comp_igc', 'sys_gtawf', status, 30)), 'CI_smoke__gfx-driver__comp_igc', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_SMOKE__open-linux-driver-ci-dev_igc', 'open-linux-driver-ci-dev_igc', 'sys_gtawf', status, 30)), 'CI_SMOKE__open-linux-driver-ci-dev_igc', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_SMOKE__ci-neo_embargo', 'ci-neo_embargo', 'sys_gtawf', status, 30)), 'CI_SMOKE__ci-neo_embargo', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_SMOKE__gfx-driver__comp_ogl', 'gfx-driver__comp_ogl', 'sys_gtawf', status, 30)), 'CI_smoke__gfx-driver__comp_ogl', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_smoke__gfx-driver__comp_igc', 'gfx-driver__comp_igc', 'sys_gtawf', status, 30)), 'CI_smoke__gfx-driver__comp_igc', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_smoke__gfx-driver__comp_vulkan', 'gfx-driver__comp_vulkan', 'sys_gtawf', status, 30)), 'CI_smoke__gfx-driver__comp_vulkan', plot_height=1000, bars_colors='#888888')

        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_daily__ci-neo_master', 'ci-neo_master', 'sys_gtawf', status, 20)), 'CI_daily__ci-neo_master', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_daily__gfx-driver__comp_glsl', 'gfx-driver__comp_glsl', 'sys_gtawf', status, 20)), 'CI_daily__gfx-driver__comp_glsl', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_daily__gfx-driver__comp_igc', 'gfx-driver__comp_igc', 'sys_gtawf', status, 20)), 'CI_daily__gfx-driver__comp_igc', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_DAILY__open-linux-driver-ci-dev_igc', 'open-linux-driver-ci-dev_igc', 'sys_gtawf', status, 20)), 'CI_DAILY__open-linux-driver-ci-dev_igc', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_daily__ci-neo_embargo', 'ci-neo_embargo', 'sys_gtawf', status, 20)), 'CI_daily__ci-neo_embargo', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_daily__gfx-driver__comp_ogl', 'gfx-driver__comp_ogl', 'sys_gtawf', status, 20)), 'CI_daily__gfx-driver__comp_ogl', plot_height=1000, bars_colors='#888888')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_DAILY__gfx-driver__comp_vulkan', 'gfx-driver__comp_vulkan', 'sys_gtawf', status, 20)), 'CI_DAILY__gfx-driver__comp_vulkan', plot_height=1000, bars_colors='#888888')
          
        '''
        ci_cycles = get_cycles('CI_DAILY__gfx-driver__master__silicon', 'gfx-driver__master', 'sys_gtawf', status, 30)
        add_plot(file_name, get_ci_cycle_stat(ci_cycles), 'CI_DAILY__gfx-driver__master__silicon', plot_height=1000, bars_colors='#ff0000')
        add_plot(file_name, get_ci_cycle_session_stat(ci_cycles), 'SESSIONS CI_DAILY__gfx-driver__master__silicon', plot_height=10000, bars_colors='#0000bb', task_key='test_plan_name_and_build')
        '''
       
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_WEEKLY__ci-neo_master', 'ci-neo_master', 'sys_gtawf', status, 10)), 'CI_WEEKLY__ci-neo_master', plot_height=1000, bars_colors='#0000ff')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_WEEKLY__ci-neo_embargo', 'ci-neo_embargo', 'sys_gtawf', status, 10)), 'CI_WEEKLY__ci-neo_embargo', plot_height=1000, bars_colors='#0000ff')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_WEEKLY__gfx-driver__comp_ogl', 'gfx-driver__comp_ogl', 'sys_gtawf', status, 10)), 'CI_WEEKLY__gfx-driver__comp_ogl', plot_height=1000, bars_colors='#0000ff')
        add_plot(file_name, get_ci_cycle_stat(get_cycles('CI_WEEKLY__gfx-driver__comp_vulkan', 'gfx-driver__comp_vulkan', 'sys_gtawf', status, 10)), 'CI_WEEKLY__gfx-driver__comp_vulkan', plot_height=1000, bars_colors='#0000ff')

        with open(file_name, 'a') as f:
            f.write('</body></html>')
        print(f'Saved the output file:{file_name}')

    '''
    #BRANCHES
    if branches:
        cache_file1_name = f'cycles_branches_tmp.cache'
        cache_file2_name = f'sessions_branches_tmp.cache'
        if offline_mode and os.path.isfile(cache_file1_name) and os.path.isfile(cache_file2_name):
            with open(cache_file1_name, 'rb') as cache:
                ci_cycle_stat = pickle.load(cache)
            with open(cache_file2_name, 'rb') as cache:
                ci_test_sessions_stat = pickle.load(cache)
        else:
            ci_cycle_stat = list()
            ci_test_sessions_stat = list()
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('ON_DEMAND_TESTS__gfx-driver__comp_media__Smoke', 'gfx-driver__comp_media', None, status, 30))

            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_smoke__ci-neo_master', 'ci-neo_master', 'sys_gtawf', status, 30))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_SMOKE__gfx-driver__comp_glsl', 'gfx-driver__comp_glsl', 'sys_gtawf', status, 30))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_smoke__gfx-driver__comp_igc', 'gfx-driver__comp_igc', 'sys_gtawf', status, 30))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_SMOKE__open-linux-driver-ci-dev_igc', 'open-linux-driver-ci-dev_igc', 'sys_gtawf', status, 30))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_SMOKE__ci-neo_embargo', 'ci-neo_embargo', 'sys_gtawf', status, 30))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_SMOKE__gfx-driver__comp_ogl', 'gfx-driver__comp_ogl', 'sys_gtawf', status, 30))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_SMOKE__gfx-driver__comp_vulkan', 'gfx-driver__comp_vulkan', 'sys_gtawf', status, 30))

            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_daily__ci-neo_master', 'ci-neo_master', 'sys_gtawf', status, 20))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_daily__gfx-driver__comp_glsl', 'gfx-driver__comp_glsl', 'sys_gtawf', status, 20))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_daily__gfx-driver__comp_igc', 'gfx-driver__comp_igc', 'sys_gtawf', status, 20))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_DAILY__open-linux-driver-ci-dev_igc', 'open-linux-driver-ci-dev_igc', 'sys_gtawf', status, 20))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_daily__ci-neo_embargo', 'ci-neo_embargo', 'sys_gtawf', status, 20))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_daily__gfx-driver__comp_ogl', 'gfx-driver__comp_ogl', 'sys_gtawf', status, 20))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_DAILY__gfx-driver__comp_vulkan', 'gfx-driver__comp_vulkan', 'sys_gtawf', status, 20))
            
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_WEEKLY__ci-neo_master', 'ci-neo_master', 'sys_gtawf', status, 10))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_WEEKLY__ci-neo_embargo', 'ci-neo_embargo', 'sys_gtawf', status, 10))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_WEEKLY__gfx-driver__comp_ogl', 'gfx-driver__comp_ogl', 'sys_gtawf', status, 10))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_WEEKLY__gfx-driver__comp_vulkan', 'gfx-driver__comp_vulkan', 'sys_gtawf', status, 10))
            with open(cache_file1_name, 'w+b') as cache:
                pickle.dump(ci_cycle_stat, cache) 
            with open(cache_file2_name, 'w+b') as cache:
                pickle.dump(ci_test_sessions_stat, cache)

    '''
    return 0

def add_plot(file_name, ci_cycles_stat, plot_title, plot_height=1200, bars_colors='#00ffff', task_key='build_name'):
    ci_cycle_df = pd.DataFrame(ci_cycles_stat)
    ci_cycle_df = ci_cycle_df.rename(columns = {task_key:'Task', 'start_date':'Start', 'end_date':'Finish'})
    fig = ff.create_gantt(ci_cycle_df, colors=bars_colors, group_tasks=True, title=plot_title, height=plot_height, showgrid_x=True)
    with open(file_name, 'a') as f:
        f.write(fig.to_html(full_html=False, include_plotlyjs='cdn'))

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


def get_ci_cycle_stat(ci_cycles):
    ci_cycle_stat = list()
    for cycle in ci_cycles:
        cycle_dict = dict()
        cycle_dict.update({'cycle_id':cycle['id']})
        for key in ['dag_id', 'submitter', 'start_date', 'status_date', 'status', 'cycle_type', 'label']:
            cycle_dict.update({key:cycle[key]})
        cycle_dict.update({'end_date':get_end_date(cycle['status_date'], cycle['status'])})    
        cycle_dict.update({'duration':get_duration(cycle['start_date'], cycle_dict['end_date'])})
        cycle_dict.update({'duration_seconds':get_duration(cycle['start_date'], cycle_dict['end_date'], seconds=True)})
        cycle_dict.update({'stream_name':cycle['builds'][0]['stream_name']})
        cycle_dict.update({'build_name':cycle['builds'][0]['name']})
        cycle_dict.update({'build_id':cycle['builds'][0]['external_id']})
        cycle_dict.update({'build_link':cycle['builds'][0]['url']})
        cycle_dict.update({'build_start_date':cycle['builds'][0]['start_date']})
        cycle_dict.update({'started_after_build':get_duration(cycle['builds'][0]['status_date'], cycle['start_date'])})
        cycle_dict.update({'started_after_build_seconds':get_duration(cycle['builds'][0]['status_date'], cycle['start_date'], seconds=True)})
        ci_cycle_stat.append(cycle_dict)
    return ci_cycle_stat


def get_ci_cycle_session_stat(ci_cycles):
    session_stat = list()
    for cycle in ci_cycles:
        for session in cycle['test_sessions']:
            session_dict = dict()
            session_dict.update({'stream_name':cycle['builds'][0]['stream_name']})
            session_dict.update({'build_name':cycle['builds'][0]['name']})
            session_dict.update({'build_id':cycle['builds'][0]['external_id']})
            session_dict.update({'build_link':cycle['builds'][0]['url']})
            session_dict.update({'cycle_id':cycle['id']})
            for key in session.keys():
                if key == 'id':
                    session_dict.update({'session_id':session[key]})
                elif key == 'external_id':
                    session_dict.update({'gtax_id':session[key]})
                else:
                    session_dict.update({key:session[key]})
            session_dict.update({'end_date':get_end_date(session['status_date'], session['status'])}) 
            session_dict.update({'duration':get_duration(session['start_date'], session_dict['end_date'])})
            session_dict.update({'duration_seconds':get_duration(session['start_date'], session_dict['end_date'], seconds=True)})
            session_dict.update({'build_and_label':f'{session_dict["build_name"]}-{session_dict["label"]}'})
            session_dict.update({'label_and_build':f'{session_dict["label"]}-{session_dict["build_name"]}'})
            session_stat.append(session_dict)
    update_sessions_with_tp_name(session_stat)
    return session_stat

def update_sessions_with_tp_name(ci_test_sessions_stat):
    test_plan_dict = get_test_plan_dict(ci_test_sessions_stat)
    for session in ci_test_sessions_stat:
        test_plan_name = get_tp_name(session['test_plan_id'], test_plan_dict)
        if test_plan_name:
            session.update({'test_plan_name':test_plan_name})
            session.update({'test_plan_name_and_build':f'{test_plan_name}-{session["build_name"]}'})
        else:
            # for null tp id
            session.update({'test_plan_name':session['label']})
            session.update({'test_plan_name_and_build':f'{session["label"]}-{session["build_name"]}'})

def get_end_date(status_date, status, time_format='%Y-%m-%dT%H:%M:%SZ'):
    end_date = status_date
    if status == 'IN PROGRESS':
        time_end = datetime.utcnow()
        end_date = time_end.strftime(time_format)
    return end_date

def get_tp_name(tp_id, test_plan_dict):
    tp_name = None
    if tp_id:
        tp_name = test_plan_dict[tp_id]
    return tp_name

def get_test_plan_dict(ci_session_stat):
    test_plan_dict = dict()
    tp_cache_file = 'tp_names.cache'
    if os.path.isfile(tp_cache_file):
        with open(tp_cache_file, 'rb') as cache:
            test_plan_dict = pickle.load(cache)
    test_plan_ids_set = set()
    for session in ci_session_stat:
        if session['test_plan_id']:
            test_plan_ids_set.add(session['test_plan_id'])
    for tp_id in test_plan_ids_set:
        if tp_id not in test_plan_dict.keys():
                test_plan_dict.update({tp_id:get_test_plan_name(tp_id)})
    with open(tp_cache_file, 'w+b') as cache:
        pickle.dump(test_plan_dict, cache) 
    return test_plan_dict

def get_test_plan_name(test_plan_id):
    url = f'http://gta.intel.com/api/tp/v1/testplans/{test_plan_id}'
    print(f'geting test plan name for {test_plan_id}')
    response = get_gta_data(url)
    test_plan = response.json()
    return test_plan['name']

def get_duration(start_date, end_date, seconds=False, time_format='%Y-%m-%dT%H:%M:%SZ'):
    duration = None
    if start_date and end_date:
        time_start = datetime.strptime(start_date, time_format)
        time_end = datetime.strptime(end_date, time_format)
        if seconds:
            duration = round((time_end - time_start).total_seconds())
        else:
            duration = str(time_end - time_start)
    return duration

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

def get_filename_timestamp():
    ts = str(datetime.now())
    ts = ts.replace(':', '_')
    return ts[5:-7]

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-s', '-status', default='ALL', help='status filter', required=False)
    ap.add_argument('-b', '-branches', action='store_true', default=False, help='include branches', required=False)
    ap.add_argument('-t', '-test_mode', action='store_true', default=False, help='offline mode', required=False)
    parsed = ap.parse_args()
    main(parsed.s, parsed.b, parsed.t)
