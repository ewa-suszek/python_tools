import sys
import math
import re
import os.path
import argparse
import pickle
from datetime import datetime
from datetime import timedelta
from operator import itemgetter
import time
import json
import requests
#import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.figure_factory as ff

def main(status, count, date_from, date_to, dag_stream, submitter, filename, offline_mode=False):
    ci_cycle_stat = list()
    ci_test_sessions_stat = list()
    ci_jobs_data = list()

    #GETING DATA
    cache_file1_name = f'smoke_cycles_master_tmp.cache'
    cache_file2_name = f'smoke_sessions_master_tmp.cache'
    cache_file3_name = f'smoke_jobs_list_dict_tmp.cache'
    cache_wf = False
    #cache_wf = True

    if cache_wf and os.path.isfile(cache_file1_name) and os.path.isfile(cache_file2_name):
        with open(cache_file1_name, 'rb') as cache:
            ci_cycle_stat = pickle.load(cache)
        with open(cache_file2_name, 'rb') as cache:
            ci_test_sessions_stat = pickle.load(cache)
        with open(cache_file3_name, 'rb') as cache:
            ci_jobs_data = pickle.load(cache)    
    else:
        if dag_stream.find(',') > 0:
            dags_list = dag_stream.split(',')
        else:
            dags_list = [dag_stream]
        for dag in dags_list:
            if dag.find(':') > 0:
                dag_name = dag.split(':')[0]
                stream_name = dag.split(':')[1]
                update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles(dag_name, stream_name, submitter, status=status, count=count, date_from=date_from, date_to=date_to))
                print(f'{len(ci_cycle_stat)} cycles and {len(ci_test_sessions_stat)} sessions found')
                update_sessions_with_tp_data(ci_test_sessions_stat)
                update_sessions_with_gtax_data(ci_test_sessions_stat, ci_jobs_data, offline_mode)
            else:
                print('wrong dag stream format. use DAG:stream exp: CI_SMOKE__gfx-driver__master:gfx-driver__master')
        with open(cache_file1_name, 'w+b') as cache:
            pickle.dump(ci_cycle_stat, cache) 
        with open(cache_file2_name, 'w+b') as cache:
            pickle.dump(ci_test_sessions_stat, cache)
        with open(cache_file3_name, 'w+b') as cache:
            pickle.dump(ci_jobs_data, cache)
    
    #print(len(ci_jobs_data_dict))

    print(ci_cycle_stat[0])
    print(ci_test_sessions_stat[0])
    print(ci_jobs_data[0])

    #print(len(ci_cycle_stat))
    #print(len(ci_test_sessions_stat))
    #print(len(ci_jobs_data))

    #data = pd.DataFrame.from_dict(ci_jobs_data)
    df_jobs = pd.DataFrame(ci_jobs_data)

    #print(ci_jobs_data[0])
    #cont = 0
    #for ci_job in ci_jobs_data:
    #    if ci_job['csq'] != 'not_found' and ci_job['jobset_id'] == 20944835:
    #        print(f"{ci_job['id']} {ci_job['session_id']} {ci_job['jobset_id']} {ci_job['name']}")
    #print(cont)

    for ci_session in ci_test_sessions_stat:
        print(f" {ci_session['gtax_id']} {ci_session['test_plan_id']} {ci_session['test_plan_name']}")


    # get list of builds:
    builds_list = list(df_jobs.groupby('build_name').groups.keys())

    pd_results = pd.DataFrame(df_jobs.groupby(['dag_id','gtax_instance','environment','platform'])['duration'].sum())
    pd_results['duration'] = pd_results['duration'].apply(seconds_to_hms)
    print(df_2_html(pd_results, f'smoke_jobs_duration_total.html'))
    pd_results = pd.DataFrame(df_jobs.groupby(['dag_id','gtax_instance','environment','platform'])['total'].sum())
    print(df_2_html(pd_results, f'smoke_task_count.html'))

    #builds_list = list()
    '''
    for build_name in builds_list:
        print(f'{build_name}')
        pd_results = pd.DataFrame(df_jobs[df_jobs['build_name'] == build_name].groupby(['gtax_instance','environment','platform','submission_type'])['duration'].sum())
        pd_results['duration'] = pd_results['duration'].apply(seconds_to_hms)
        print(df_2_html(pd_results, f'{build_name}_jobs_duration.html'))
        pd_results = pd.DataFrame(df_jobs[df_jobs['build_name'] == build_name].groupby(['gtax_instance','environment','platform'])['duration'].sum())
        pd_results['duration'] = pd_results['duration'].apply(seconds_to_hms)
        print(df_2_html(pd_results, f'{build_name}_jobs_duration_total.html'))
        pd_results = pd.DataFrame(df_jobs[df_jobs['build_name'] == build_name].groupby(['gtax_instance','environment','platform','submission_type'])['total'].sum())
        print(df_2_html(pd_results, f'{build_name}_task_count.html'))

        pd_results = pd.DataFrame(df_jobs[df_jobs['build_name'] == build_name].groupby(['gtax_instance','environment','platform','submission_type']).agg({'total': 'sum'}).groupby(level=['gtax_instance','platform']).apply(lambda x: round(100 * x / float(x.sum()), 2)))
        print(df_2_html(pd_results, f'{build_name}_task_count_percent.html'))

        pd_results = pd.DataFrame(df_jobs[df_jobs['build_name'] == build_name].groupby(['gtax_instance','environment','platform','submission_type']).agg({'duration': 'sum'}).groupby(level=['gtax_instance','platform']).apply(lambda x: round(100 * x / float(x.sum()), 2)))
        print(df_2_html(pd_results, f'{build_name}_task_duration_percent.html'))

        pd_results = pd.DataFrame(df_jobs[df_jobs['build_name'] == build_name].groupby(['gtax_instance','environment','platform'])['total'].sum())
        print(df_2_html(pd_results, f'{build_name}_task_count_total.html'))

        
        pd_results = pd.DataFrame(df_jobs[df_jobs['build_name'] == build_name].groupby(['platform'])['total'].sum())
        print(gen_bar_plot(pd_results, f'{build_name}_task_count_total', 'platform', 'total_tasks', f'{build_name}_task_count_total.png'))

        pd_results = pd.DataFrame(df_jobs[(df_jobs['build_name'] == build_name) & (df_jobs['submission_type'] == 'init')].groupby(['platform'])['total'].sum())
        print(gen_bar_plot(pd_results, f'{build_name}_init_task_count_total', 'platform', 'total_init_tasks', f'{build_name}_init_task_count_total.png'))

        pd_results = pd.DataFrame(df_jobs[(df_jobs['build_name'] == build_name) & (df_jobs['submission_type'] == 'init') & (df_jobs['gtax_instance'] == 'gtax-igk-smoke')].groupby(['platform'])['total'].sum())
        print(gen_bar_plot(pd_results, f'{build_name}_init_task_count_total_igk', 'platform', 'init_tasks', f'{build_name}_init_task_count_total_igk.png'))

        pd_results = pd.DataFrame(df_jobs[(df_jobs['build_name'] == build_name) & (df_jobs['gtax_instance'] == 'gtax-igk-smoke')].groupby(['platform'])['duration'].sum())
        pd_results['duration'] = pd_results['duration'].apply(seconds_to_h)
        print(gen_bar_plot(pd_results, f'{build_name}_jobs_duration_igk', 'platform', 'duration', f'{build_name}_jobs_duration_igk.png'))

        pd_results = pd.DataFrame(df_jobs[(df_jobs['build_name'] == build_name) & (df_jobs['submission_type'] == 'init') & (df_jobs['gtax_instance'] == 'gtax-shared-fm')].groupby(['platform'])['total'].sum())
        print(gen_bar_plot(pd_results, f'{build_name}_init_task_count_total_fm', 'platform', 'init_tasks', f'{build_name}_init_task_count_total_fm.png'))

        pd_results = pd.DataFrame(df_jobs[(df_jobs['build_name'] == build_name) & (df_jobs['gtax_instance'] == 'gtax-shared-fm')].groupby(['platform'])['duration'].sum())
        pd_results['duration'] = pd_results['duration'].apply(seconds_to_h)
        print(gen_bar_plot(pd_results, f'{build_name}_jobs_duration_fm', 'platform', 'duration', f'{build_name}_jobs_duration_fm.png'))


        #### platform TP instance min-max time
        pd_results = pd.DataFrame(df_jobs[df_jobs['build_name'] == build_name].groupby(['gtax_instance','test_plan_id','test_plan_name','platform'])['started_date'].min())
        start_time_dict = pd_results.to_dict()
        pd_results = pd.DataFrame(df_jobs[df_jobs['build_name'] == build_name].groupby(['gtax_instance','test_plan_id','test_plan_name','platform'])['completed_date'].max())
        end_time_dict = pd_results.to_dict()
        print(add_plot(f'{build_name}_instance_tp_platform_GRAPH.html', get_platform_timeline(start_time_dict, end_time_dict), build_name, plot_height=5000, bars_colors='#888888', task_key='timeline_key'))
    '''
    #df = [dict(Task="Job A", Start='2009-01-01', Finish='2009-02-28'), dict(Task="Job B", Start='2009-03-05', Finish='2009-04-15'), dict(Task="Job C", Start='2009-02-20', Finish='2009-05-30')]
    print(add_plot('smoke_cycles_GRAPH.html', ci_cycle_stat, 'master', plot_height=5000, bars_colors='#ff0000'))
    print(add_plot('smoke_cycles_GRAPH_sorted.html', ci_cycle_stat, 'master', plot_height=5000, bars_colors='#ff0000', sort_by='Start'))
    print(add_plot('smoke_sessions_GRAPH.html', ci_test_sessions_stat, 'master', plot_height=15000, bars_colors='#0000bb', task_key='test_plan_name_and_build'))
    print(add_plot('smoke_sessions_GRAPH_sorted.html', ci_test_sessions_stat, 'master', plot_height=15000, bars_colors='#0000bb', task_key='test_plan_name_and_build', sort_by='Start'))

    print("")
    return 0

def int_2_str(int_vale):
    return str(int_vale)

def add_plot(file_name, ci_cycles_stat, plot_title, plot_height=1200, bars_colors='#00ffff', task_key='build_name', sort_by=None):
    with open(file_name, 'w') as f:
        f.write('<html><head><meta charset="utf-8" /></head><body>')
    ci_cycle_df = pd.DataFrame(ci_cycles_stat)
    ci_cycle_df = ci_cycle_df.rename(columns = {task_key:'Task', 'start_date':'Start', 'end_date':'Finish'})
    if sort_by:
        ci_cycle_df.sort_values(by=[sort_by], inplace=True)
    fig = ff.create_gantt(ci_cycle_df, colors=bars_colors, group_tasks=True, title=plot_title, height=plot_height, showgrid_x=True)
    with open(file_name, 'a') as f:
        f.write(fig.to_html(full_html=False, include_plotlyjs='cdn'))
    with open(file_name, 'a') as f:
        f.write('</body></html>')
    return f'file saved: {file_name}'

def gen_bar_plot(df, title, x_title, y_title, file_name):
    plot_data = dict()
    df_dict = df.to_dict()
    for key in df_dict.keys():
        x_list = list()
        y_list = list()
        for sub_key in df_dict[key].keys():
            x_list.append(sub_key)
            y_list.append(df_dict[key][sub_key])
    plot_data.update({x_title:x_list})
    plot_data.update({y_title:y_list})
    df = pd.DataFrame(plot_data,columns=[x_title, y_title])
    df.plot(x = x_title, y=y_title, kind = 'bar')
    for i in range(len(y_list)):
        plt.annotate(str(y_list[i]), xy=(i,y_list[i]), ha='center', va='bottom', rotation=0)
    plt.legend(loc='lower center', bbox_to_anchor=(0.5, 1.05))
    plt.title(title, y=1.25)
    plt.tight_layout()
    plt.savefig(file_name, dpi=150)
    return f'file saved: {file_name}'

def get_platform_timeline(start_time_dict, end_time_dict):
    platform_timeline = list()
    for key in start_time_dict.keys():
        s_dict = dict()
        for sub_key in start_time_dict[key].keys():
            s_dict.update({'_'.join(sub_key):start_time_dict[key][sub_key]})
    for key in end_time_dict.keys():
        e_dict = dict()
        for sub_key in end_time_dict[key].keys():
            e_dict.update({'_'.join(sub_key):end_time_dict[key][sub_key]})
    for key in s_dict.keys():
        platform_timeline.append({'timeline_key':key, 'start_date': s_dict[key], 'end_date':e_dict[key]})
    return platform_timeline

def df_2_html(df, file_name):
    html = '<!DOCTYPE html><html><head><style>table {font-family:Verdana;font-size: 10px; border-collapse: collapse;} table, th, td {border: 1px solid black; padding-left: 5px; padding-right: 5px; padding-top: 2px; padding-bottom: 2px;} tr:nth-child(even) {background-color: #f2f2f2;}</style></head><body><div style="overflow-x:auto;">'
    html += df.to_html()
    html += '</div></body></html>' 
    with open(file_name, 'w') as out_file:
        out_file.write(html)
    return f'file saved: {file_name}'

def seconds_to_hms(seconds):
    seconds = int(seconds)
    hrs = seconds // 3600
    min = (seconds % 3600) // 60
    sec = seconds % 60
    return f'{hrs}:{min:02d}:{sec:02d}'

def seconds_to_h(seconds):
    seconds = int(seconds)
    hrs = round(seconds/3600)
    min = (seconds % 3600) // 60
    return hrs

def get_key_set(report_data, key):
    value_set = set()
    for data in report_data:
        value_set.add(report_data[data][key])
    return value_set

def update_stats(ci_cycle_stat, ci_test_sessions_stat, cycles):
    ci_cycle_stat += get_ci_cycle_stat(cycles)
    ci_test_sessions_stat += get_ci_cycle_session_stat(cycles)
    return 0


def get_cycles(dag_id, stream, submitter=None, date_from=None, date_to=None, status=None, count=100):
    cycles_list = list()
    url = f'http://gta.intel.com/api/workflow/v2/test_runs_dashboard?count={count}&filter%5Bdag_id%5D={dag_id}'
    print(f'geting cycles  dag_id:{dag_id}', end=' ') 
    if submitter:
        url += f'&filter%5Bsubmitter%5D={submitter}'
        print(f'submitter:{submitter}', end=' ')
    if stream:
        url += f'&filter%5Bstream%5D={stream}'
        print(f'stream:{stream}', end=' ')
    if status in ['NEW', 'IN PROGRESS' ,'COMPLETED', 'ERROR', 'TIMEOUT', 'INCOMPLETE']:
        url += f'&filter%5Bstatus%5D={status}'
        print(f'status:{status}', end=' ')
    if status == 'DEFAULT':
        url += '&filter%5Bstatus%5D!=NEW&filter%5Bstatus%5D!=IN%20PROGRESS'
        print('status: !NEW AND !IN PROGRESS', end=' ')
    if date_from:
        url += f'&filter%5Btest_run_start_date%5D=%3E{date_from}T00%3A00%3A00Z'        
        print(f'date_from:{date_from}', end=' ')
    if date_to:
        url += f'&filter%5Btest_run_start_date%5D=%3C{date_to}T23%3A59%3A59Z'
        print(f'date_to:{date_to}', end=' ')
    url += '&sorting%5Bid%5D=desc&filter%5Bexact_dag_id%5D=true'
    print(' ')
    print(url)
    cycles_list = get_gta_cycles_pages(url)
    return cycles_list


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
        cycle_dict.update({'build_name':cycle['builds'][0]['name'].replace('/','_')})
        cycle_dict.update({'build_id':cycle['builds'][0]['external_id']})
        cycle_dict.update({'build_link':cycle['builds'][0]['url']})
        cycle_dict.update({'build_start_date':cycle['builds'][0]['start_date']})
        cycle_dict.update({'started_after_build':get_duration(cycle['builds'][0]['status_date'], cycle['start_date'])})
        cycle_dict.update({'started_after_build_seconds':get_duration(cycle['builds'][0]['status_date'], cycle['start_date'], seconds=True)})
        cycle_dict.update({'lgcb_bad':get_flag_status(cycle['test_sessions'], 'lgcb_bad')})
        cycle_dict.update({'has_regressions':get_flag_status(cycle['test_sessions'], 'has_regressions')})
        cycle_dict.update({'comparison_view':get_cycle_comparison_view_link(cycle['builds'][0]['name'], cycle['id'])})
        cycle_dict.update({'WW':convert_to_intel_ww(cycle['start_date'])})
        ci_cycle_stat.append(cycle_dict)
    return ci_cycle_stat

def get_flag_status(session_list, flag_name):
    flag_status = False
    for session in session_list:
        if session[flag_name]:
            flag_status = True
            break
    return flag_status

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
            session_dict.update({'dag_id':cycle['dag_id']})
            for key in session.keys():
                if key == 'id':
                    session_dict.update({'session_id':session[key]})
                elif key == 'external_id':
                    session_dict.update({'gtax_id':session[key]})
                elif key == 'url':
                    url = session[key]
                    session_dict.update({'url':url})
                    if url:
                        instance_start = url.find('//') + 2
                        instance_end = url.find('.intel.com')
                        session_dict.update({'gtax_instance':url[instance_start:instance_end]})
                    else:
                        session_dict.update({'gtax_instance':''})
                elif key == 'cycle_type':
                    session_dict.update({key:cycle[key]})
                elif key == 'test_session_failure':
                    failure_reasons_set = set()
                    if 'comment' in session['test_session_failure'].keys():
                        session_dict.update({'comments':str(session['test_session_failure']['comment'])})
                    else:
                        session_dict.update({'comments':'None'})
                    if 'categories' in session['test_session_failure'].keys():
                        for category in session['test_session_failure']['categories']:
                            if category['selected']:
                                reason_set = set()
                                for reason in category['values']:
                                    if reason['selected']:
                                        # WA for "GTA (WF, RES, TP)" - > "GTA (WF-RES-TP)"
                                        reason_set.add(reason['name'].replace(', ','-'))
                                if len(reason_set) > 0:
                                    failure_reasons_set.add(f"{category['name']}:{','.join(reason_set)}")
                                else:
                                    failure_reasons_set.add(category['name'])
                    if len(failure_reasons_set) > 0:
                        session_dict.update({'failure_reasons':','.join(failure_reasons_set)})
                    else:
                        session_dict.update({'failure_reasons':'None'})
                else:
                    session_dict.update({key:session[key]})
            session_dict.update({'end_date':get_end_date(session['status_date'], session['status'])}) 
            session_dict.update({'duration':get_duration(session['start_date'], session_dict['end_date'])})
            session_dict.update({'duration_seconds':get_duration(session['start_date'], session_dict['end_date'], seconds=True)})
            if session_dict['duration_seconds']:
                session_dict.update({'duration_min':round(session_dict['duration_seconds']/60, 0)})
            else:
                session_dict.update({'duration_min':'N/A'})
            session_dict.update({'comparison_view':get_session_comparison_view_link(cycle['builds'][0]['name'], cycle['id'], session['id'])})
            session_dict.update({'WW':convert_to_intel_ww(cycle['start_date'])})
            session_stat.append(session_dict)
    return session_stat
    
def get_cycle_comparison_view_link(build_name, cycle_id, worst=False):
    url = 'https://gta.intel.com/#/reports/comparison-view?diffMode=false&reRuns[name]=all&table[page]=1&table[count]=25&visibleColumns[]=Item%20Name&visibleColumns[]=Args&visibleColumns[]=OS&visibleColumns[]=Platform&visibleColumns[]=Vertical&visibleColumns[]=Test%20Run&visibleColumns[]=Test%20Session&compareFields[]=compare_id&settingsFromUrl=true&tagExcept[0][name]=notAnIssue&tagExcept[1][name]=obsoleted&tagExcept[2][name]=iteration&tagExcept[3][name]=isolation'
    if worst:
        url += '&rerun=Worst'
    url += f'&globalFilterId=&builds[0][name]={build_name}&builds[0][key]={build_name}&filters[test_run][0][name]={cycle_id}'
    return url

def get_session_comparison_view_link(build_name, cycle_id, session_id):
    url = get_cycle_comparison_view_link(build_name, cycle_id, worst=True)
    url += f'&filters[test_session][0][name]={session_id}'
    return url

def update_sessions_with_tp_data(ci_test_sessions_stat):
    test_plan_dict = get_test_plan_dict(ci_test_sessions_stat)
    for session in ci_test_sessions_stat:
        if session['test_plan_id'] in test_plan_dict.keys():
            session.update({'test_plan_name':get_tp_name(session['test_plan_id'], test_plan_dict)})
            session.update({'environment':get_tp_env(session['test_plan_id'], test_plan_dict)})
            session.update({'test_plan_name_and_build':f"{get_tp_name(session['test_plan_id'], test_plan_dict)}-{session['build_name']}"})
        else:
            # for null tp id
            session.update({'test_plan_name':session['label']})
            session.update({'environment':'unknown'})
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
        tp_name = test_plan_dict[tp_id]['name']
    return tp_name

def get_tp_env(tp_id, test_plan_dict):
    tp_env = 'unknown'
    if tp_id:
        tp_env = test_plan_dict[tp_id]['env']
    return tp_env

def get_test_plan_dict(ci_session_stat):
    test_plan_dict = dict()
    tp_cache_file = 'smoke_stat_tp_dict.cache'
    if os.path.isfile(tp_cache_file):
        with open(tp_cache_file, 'rb') as cache:
            test_plan_dict = pickle.load(cache)
    test_plan_ids_set = set()
    for session in ci_session_stat:
        if session['test_plan_id']:
            test_plan_ids_set.add(session['test_plan_id'])
    for tp_id in test_plan_ids_set:
        if tp_id not in test_plan_dict.keys():
                tp_data = get_test_plan_data(tp_id)
                test_plan_dict.update({tp_id:{'name':tp_data['name'], 'env':tp_data['env']}})
    with open(tp_cache_file, 'w+b') as cache:
        pickle.dump(test_plan_dict, cache) 
    return test_plan_dict

def get_test_plan_data(test_plan_id):
    url = f'http://gta.intel.com/api/tp/v1/testplans/{test_plan_id}'
    print(f'geting test plan data for {test_plan_id}')
    response = get_gta_data(url)
    test_plan = response.json()
    tp_data = dict()
    tp_env = 'unknown'
    tp_data.update({'name':test_plan['name']})
    for attribute in test_plan['attributes']:
        if attribute['name'] == 'Environment':
            tp_env = attribute['resolvedValue']
    tp_data.update({'env':tp_env})
    return tp_data

def get_duration(start_date, end_date, seconds=False, time_format='%Y-%m-%dT%H:%M:%SZ', timedate_format=False):
    duration = None
    if start_date and end_date:
        if timedate_format:
            time_start = start_date
            time_end = end_date
        else:
            time_start = datetime.strptime(start_date, time_format)
            time_end = datetime.strptime(end_date, time_format)
        if seconds:
            duration = round((time_end - time_start).total_seconds())
        else:
            duration = str(time_end - time_start)
    return duration

def update_sessions_with_gtax_data(ci_test_sessions_stat, ci_jobs_data, offline_mode=False):
    call_count = 0
    call_total = len(ci_test_sessions_stat)
    for session in ci_test_sessions_stat:
        call_count += 1
        if session['gtax_id']:
            print(f'getting gtax data {round(call_count/call_total*100,2)}%   ', end='\r', flush=True)
            jobs_full_info = get_gtax_jobs_full_info(session['gtax_instance'], session['gtax_id'], offline_mode)
            #session_jobs_dict = get_session_jobs_dict(jobs_full_info, session['gtax_instance'], session['build_name'])
            #ci_jobs_data.update(session_jobs_dict)
            session_jobs_list = get_session_jobs_list(jobs_full_info, session)
            ci_jobs_data += session_jobs_list
            #max_job_duration = get_max_job_duration(session_jobs_dict)
            #session.update({'max_job_duration':max_job_duration})
            #session.update({'tpt_met':get_tpt_met(session['duration_min'], 60)})
        else:
            for key in ['setup_tasks_total', 'setup_tasks_success', 'setup_success', 'test_tasks_total', 'test_tasks_worst_success', 'test_tasks_best_success', 'test_best', 'test_worst', 'test_best_worst', 'max_job_duration', 'tpt_met']:
                session.update({key:'N/A'})
    print('\n')

def get_max_job_duration(session_jobs_dict):
    max_duration = 0
    for job in session_jobs_dict:
        if isinstance(session_jobs_dict[job]['duration'], (float, int)):
            if int(session_jobs_dict[job]['duration']) > max_duration:
                max_duration = round(int(session_jobs_dict[job]['duration'])/60, 0)
    return max_duration

def get_tpt_met(max_job_duration, limit):
    if max_job_duration > limit:
        tpt_met = 0
    else:
        tpt_met = 100
    return tpt_met

def get_stat_key_value(stat_dict, key, if_not_found=0):
    stat_key_value = if_not_found
    if key in stat_dict.keys():
        stat_key_value = stat_dict[key]
    if not isinstance(stat_key_value, (float, int)):
        stat_key_value = if_not_found
    return stat_key_value
        
def get_session_jobs_dict(session_jobs_data, gtax_instance, build_name):
    session_jobs_dict = dict()
    for job_data in session_jobs_data:
        job_dict = dict()
        for key in ['id', 'status', 'name', 'result', 'submission_type', 'submitted_date', 'started_date', 'completed_date', 'duration', 'scheduler_account_name', 'dumps_produced']:
            job_dict.update({key:job_data[key]})
        job_dict.update({'build_name':build_name})
        for key in ['client']:
            for sub_key in ['name','id']:
                key_name = f'{key}_{sub_key}'
                job_dict.update({key_name:job_data[key][sub_key]})
            if 'csq' in job_data.keys():
                job_dict.update({'platform':get_client_platform(job_data['csq']['query'])})
                job_dict.update({'pool':get_client_pool(job_data['csq']['query'])})
                if job_dict['platform'] == 'unknown':
                    if job_dict['client_id']:
                        job_dict.update({'platform':get_client_property_by_client_id(job_dict['client_id'], 'platform', gtax_instance)})
                #if job_dict['pool'] == 'unknown':
                #    if job_dict['client_id']:
                #        job_dict.update({'pool':get_client_property_by_client_id(job_dict['client_id'], 'pool', gtax_instance)})
            else:
                job_dict.update({'platform':get_client_property_by_client_id(job_dict['client_id'], 'platform', gtax_instance)})
                job_dict.update({'pool':get_client_property_by_client_id(job_dict['client_id'], 'pool', gtax_instance)})
        if 'results_summary' not in job_data.keys():
            print(job_data)
        for key in ['results_summary']:
            for sub_key in job_data[key].keys():
                key_name = f'{sub_key}'
                job_dict.update({key_name:job_data[key][sub_key]})
        if 'csq' in job_data.keys():
            job_dict.update({'csq':job_data['csq']['query']})
        else:
            job_dict.update({'csq':'not_found'})
        job_dict.update({'gtax_instance':gtax_instance})
        session_jobs_dict.update({job_data['id']:job_dict})
    return session_jobs_dict

def get_session_jobs_list(session_jobs_data, session):
    session_jobs_list = list()
    for job_data in session_jobs_data:
        job_dict = dict()
        for key in ['id', 'status', 'name', 'result', 'submission_type', 'submitted_date', 'started_date', 'completed_date', 'duration', 'scheduler_account_name', 'dumps_produced', 'jobset_session_id', 'jobset_id']:
            if key in ['duration'] and isinstance(job_data[key], str):
                job_dict.update({key:0})
            elif key in ['jobset_session_id', 'jobset_id']:
                job_dict.update({key:str(job_data[key])})
            else:
                job_dict.update({key:job_data[key]})
        for key in ['client']:
            for sub_key in ['name','id']:
                key_name = f'{key}_{sub_key}'
                job_dict.update({key_name:job_data[key][sub_key]})
            if 'csq' in job_data.keys():
                job_dict.update({'platform':get_client_platform(job_data['csq']['query'])})
                job_dict.update({'pool':get_client_pool(job_data['csq']['query'])})
                if job_dict['platform'] == 'unknown':
                    if job_dict['client_id']:
                        job_dict.update({'platform':get_client_property_by_client_id(job_dict['client_id'], 'platform', session['gtax_instance'])})
            else:
                job_dict.update({'platform':get_client_property_by_client_id(job_dict['client_id'], 'platform', session['gtax_instance'])})
                job_dict.update({'pool':get_client_property_by_client_id(job_dict['client_id'], 'pool', session['gtax_instance'])})
        if 'results_summary' not in job_data.keys():
            print(job_data)
        for key in ['results_summary']:
            for sub_key in job_data[key].keys():
                key_name = f'{sub_key}'
                job_dict.update({key_name:job_data[key][sub_key]})
        if 'csq' in job_data.keys():
            job_dict.update({'csq':job_data['csq']['query']})
        else:
            job_dict.update({'csq':'not_found'})
        for key in ['build_name', 'gtax_instance', 'cycle_id', 'session_id', 'test_plan_id', 'test_plan_name', 'environment', 'dag_id']:
            job_dict.update({key:session[key]})
        #for key in ['id']:
        #    job_dict.update({f'session_{key}':session[key]})
        session_jobs_list.append(job_dict)
    return session_jobs_list

def get_client_platform(csq):
    platform_regex = re.compile(r"('platform' = '.*?')") 
    platform = 'unknown'
    if platform_regex.search(csq):
        platform = platform_regex.search(csq).group(0)[14:-1]
    return platform

def get_client_property_by_client_id(client_id, property_name, gtax_instance):
    property_value = 'unknown'
    app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    cache_path = os.path.join(app_path, '_cache')
    cache_file_name = os.path.join(cache_path, f"client_{gtax_instance}_{client_id}_properties.cache")
    if os.path.isfile(cache_file_name):
        with open(cache_file_name, 'rb') as cache:
            client_properties = pickle.load(cache)
    else:
        url = f'http://{gtax_instance}.intel.com/api/v1/clients/{client_id}/properties'
        client_properties = get_gtax_data(url)
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        with open(cache_file_name, 'w+b') as cache:
            pickle.dump(client_properties, cache)
    if property_name in client_properties['user_defined'].keys():
        property_value = client_properties['user_defined'][property_name]
    else:
        if property_name in client_properties['auto_detected'].keys():
            property_value = client_properties['auto_detected'][property_name]
    return property_value

def get_client_pool(csq):
    platform_regex = re.compile(r"('pool' = '.*?')") 
    platform = 'unknown'
    if platform_regex.search(csq):
        platform = platform_regex.search(csq).group(0)[10:-1]
    return platform   

def get_task_phase(gta_result_key):
    phase = 'unknown'
    if gta_result_key: 
        for phase_name in ['teardown', 'setup', 'test']:
            if gta_result_key.find(phase_name) > 0:
                phase = phase_name
    else:
        phase = ''
    return phase

def get_gtax_jobs_full_info(gtax_instance, job_set_session_id, offline_mode=False):
    app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    cache_path = os.path.join(app_path, '_cache')
    cache_file_name = os.path.join(cache_path, f"smoke_gtax_{job_set_session_id}_full_info.cache")
    url = f'http://{gtax_instance}.intel.com/api/v1/jobs?include_tasks=false&include_taskml=false&include_csq=true&full_info=false&jobset_session_ids={job_set_session_id}'
    if offline_mode and os.path.isfile(cache_file_name):
        with open(cache_file_name, 'rb') as cache:
            jobs_full_info = pickle.load(cache)
        #print(cache_file_name)
    else:
        #print(f'be patient!! - getting full info of tasks for job set session: {job_set_session_id}')
        #url = f'http://{gtax_instance}.intel.com/api/v1/jobs?include_tasks=true&include_csq=true&include_phases_task_counts=true&full_info=true&jobset_session_ids={job_set_session_id}'
        url = f'http://{gtax_instance}.intel.com/api/v1/jobs?include_tasks=false&include_taskml=false&include_csq=true&full_info=false&jobset_session_ids={job_set_session_id}'
        #print(url)
        data = get_gtax_data(url)
        jobs_full_info = data['data']
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        with open(cache_file_name, 'w+b') as cache:
            pickle.dump(jobs_full_info, cache) 
    return jobs_full_info

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

def get_gta_data(url, page=None):
    output = None
    headers = { 'Content-type': 'application/json' }
    if page:
        url += f'&page={page}'
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    if response.status_code == 200:
        output = response
    else:
        print(response.status_code)
        print(response)
    return output

def get_gta_cycles_pages(url):
    cycles_list = list()
    page = 1
    response = get_gta_data(url, page=page)
    cycles = response.json()
    cycles_list.extend(cycles['items'])
    pages = cycles['pages']
    if pages > 1:
        for i in range(page+1, pages+1):
            response = get_gta_data(url, page=i)
            cycles = response.json()
            cycles_list.extend(cycles['items'])
    return cycles_list

def get_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response.json()

def get_filename_timestamp():
    ts = str(datetime.now())
    ts = ts.replace(':', '_')
    return ts[5:-7]

def get_date_n_days_ago(days_ago):
    ts = str(datetime.now()- timedelta(days=days_ago))
    return ts[0:10]

def check_user_input(user_input):
    try:
        datetime.strptime(user_input, '%Y-%m-%d')
    except ValueError:
        return False
    return True

def convert_to_intel_ww(date_string):
    #correct to Intel WW
    date_time = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ')
    iso_year = date_time.isocalendar()[0]
    iso_ww = date_time.isocalendar()[1]
    max_iso_ww = datetime.strptime(f'{iso_year}-12-31', '%Y-%m-%d').isocalendar()[1]
    first_day_of_the_year = int(datetime.strptime(f'{iso_year}-01-01', '%Y-%m-%d').strftime("%w"))
    last_day_of_the_year = int(datetime.strptime(f'{iso_year}-12-31', '%Y-%m-%d').strftime("%w"))
    day_of_year = int(date_time.strftime("%j"))
    if first_day_of_the_year in [0, 1, 2, 3, 4]:
        intel_ww = iso_ww
    else:
        intel_ww = iso_ww + 1
    if iso_ww == max_iso_ww:
        if last_day_of_the_year != 6:
            intel_ww = 1
    if day_of_year == 1 and intel_ww > 1:
        intel_ww = 1
    return f'{str(iso_year)[2:]}WW{str(intel_ww).zfill(2)}'

if __name__ == '__main__':
    ts = get_filename_timestamp()
    filename = f'smoke_tpt_report_{ts}.xlsx'
    ap = argparse.ArgumentParser()
    ap.add_argument('-s', '-status', default='COMPLETED', help='status filter values: [NEW, IN PROGRESS ,COMPLETED, ERROR, TIMEOUT, INCOMPLETE]', required=False)
    ap.add_argument('-i', '-interactive', action='store_true', default=False, help='interactive mode', required=False)
    ap.add_argument('-f', '-date_from', default=get_date_n_days_ago(7), help='date from format yyyy-mm-dd', required=False)
    ap.add_argument('-t', '-date_to', default=get_date_n_days_ago(1), help='date to format yyyy-mm-dd', required=False)
    ap.add_argument('-submitter', default='sys_gtawf', help='submitter default:sys_gtawf', required=False)
    ap.add_argument('-dag', default='CI_SMOKE__gfx-driver__master:gfx-driver__master,CI_SMOKE__agama_ci_prerelease:agama_ci_prerelease,CI_SMOKE__agama_master:agama_master,CI_SMOKE__gfx-driver__comp_vulkan:gfx-driver__comp_vulkan,CI_SMOKE__gfx-driver__comp_ogl:gfx-driver__comp_ogl,CI_SMOKE__ci-neo_embargo:ci-neo_embargo,ON_DEMAND_TESTS__gfx-driver__comp_media__Smoke:gfx-driver__comp_media,CI_SMOKE__open-linux-driver-ci-dev_igc:open-linux-driver-ci-dev_igc,CI_SMOKE__gfx-driver__comp_igc:gfx-driver__comp_igc,CI_SMOKE__gfx-driver__comp_glsl:gfx-driver__comp_glsl,CI_SMOKE__ci-neo_master:ci-neo_master', help='DAG stream default: CI_SMOKE__gfx-driver__master:gfx-driver__master,CI_SMOKE__agama_ci_prerelease:agama_ci_prerelease,CI_SMOKE__agama_master:agama_master,CI_SMOKE__gfx-driver__comp_vulkan:gfx-driver__comp_vulkan,CI_SMOKE__gfx-driver__comp_ogl:gfx-driver__comp_ogl,CI_SMOKE__ci-neo_embargo:ci-neo_embargo,ON_DEMAND_TESTS__gfx-driver__comp_media__Smoke:gfx-driver__comp_media,CI_SMOKE__open-linux-driver-ci-dev_igc:open-linux-driver-ci-dev_igc,CI_SMOKE__gfx-driver__comp_igc:gfx-driver__comp_igc,CI_SMOKE__gfx-driver__comp_glsl:gfx-driver__comp_glsl,CI_SMOKE__ci-neo_master:ci-neo_master', required=False)
    ap.add_argument('-o', '-output', default=filename, help='output file name', required=False)
    parsed = ap.parse_args()
    date_from = parsed.f
    date_to = parsed.t
    if parsed.i:
        date_from = input(f'provide from date (YYYY-MM-DD) [enter use default={get_date_n_days_ago(7)}]:')
        if not check_user_input(date_from):
            date_from = get_date_n_days_ago(7)
        date_to = input(f'provide to date (YYYY-MM-DD) [enter use default={get_date_n_days_ago(1)}]:')
        if not check_user_input(date_to):
            date_to = get_date_n_days_ago(1)
    main(parsed.s, 100, date_from, date_to, parsed.dag, parsed.submitter, parsed.o, True)
