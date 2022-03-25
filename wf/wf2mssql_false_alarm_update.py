import sys
import math
import pyodbc
import re
import os.path
import argparse
import pickle
from datetime import datetime
from datetime import timedelta
from operator import add, itemgetter
import time
import json
import requests
from requests.auth import HTTPBasicAuth
import gzip


def main(status, count, date_from, date_to, dag_stream, submitter, offline_mode=False):
    return_code = 0
    sql_server = 'gksisql017n1.ger.corp.intel.com,3181'
    sql_db_name = 'GSE_CI'
    ci_cycle_stat = list()
    ci_test_sessions_stat = list()

    #GETING DATA
    cache_file1_name = f'smoke_cycles_master_tmp.cache'
    cache_file2_name = f'smoke_sessions_master_tmp.cache'

    cycles_id_list_mssql = get_mssql_data(sql_server, sql_db_name, f"SELECT cycle_id,start_date,status_date FROM [GSE_CI].[dbo].[smoke_ci_cycles] where start_date > '{date_from}' and start_date < '{date_to} 23:59:59.999'")
    # note! status SKIPPED and ERROR do not have start date!
    sessions_id_list_mssql = get_mssql_data(sql_server, sql_db_name, f"SELECT session_id,start_date,status_date,failure_reasons,false_alarm,comments FROM [GSE_CI].[dbo].[smoke_ci_sessions] where (start_date > '{date_from}' and start_date < '{date_to} 23:59:59.999') or (start_date is NULL and status_date > '{date_from}' and status_date < '{date_to} 23:59:59.999')")

    sessions_id_dict_mssql = list2dict(sessions_id_list_mssql, index_key='session_id')
    #cycles_id_list_wf = get_cycles('CI_SMOKE__gfx-driver__master', 'gfx-driver__master', 'sys_gtawf', '2021-01-01', get_date_n_days_ago(1), 'DEFAULT', 100)


    #print(cycles_id_list_mssql[0]['start_date'])
    #print(cycles_id_list_wf[0]['start_date'])

    #gksisql017n1.ger.corp.intel.com\gksisql017n1,3181
    offline_mode = True
    offline_mode = False

    if offline_mode and os.path.isfile(cache_file1_name) and os.path.isfile(cache_file2_name):
        with open(cache_file1_name, 'rb') as cache:
            ci_cycle_stat = pickle.load(cache)
        with open(cache_file2_name, 'rb') as cache:
            ci_test_sessions_stat = pickle.load(cache)
    else:
        if dag_stream.find(':') > 0:
            dag_name = dag_stream.split(':')[0]
            stream_name = dag_stream.split(':')[1]
            #update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles('CI_SMOKE__gfx-driver__master', 'gfx-driver__master', 'sys_gtawf', '2021-01-01', get_date_n_days_ago(1), 'DEFAULT', 100))
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles(dag_name, stream_name, submitter, status=status, count=count, date_from=date_from, date_to=date_to))
            print(f'{len(ci_cycle_stat)} cycles and {len(ci_test_sessions_stat)} smoke sessions found')
            update_sessions_with_tp_data(ci_test_sessions_stat)
            with open(cache_file1_name, 'w+b') as cache:
                pickle.dump(ci_cycle_stat, cache) 
            with open(cache_file2_name, 'w+b') as cache:
                pickle.dump(ci_test_sessions_stat, cache)
        else:
            print('wrong dag stream format. use DAG:stream exp: CI_SMOKE__gfx-driver__master:gfx-driver__master')
            return 1                
    
    print(f'   WF cycles:{len(ci_cycle_stat)}')
    print(f'MSSQL cycles:{len(cycles_id_list_mssql)}')
    cycles_id_list_mssql_ids = get_ids(cycles_id_list_mssql,'cycle_id')
    for cycle in ci_cycle_stat:
        if cycle['cycle_id'] not in cycles_id_list_mssql_ids:
            print(cycle)
            return_code += 1
    print('')
    print(f'    WF session:{len(ci_test_sessions_stat)}')
    print(f'MSSQL sessions:{len(sessions_id_list_mssql)}\n')

    sessions_id_list_mssql = get_ids(sessions_id_list_mssql,'session_id')
    mssql_update_commands = ''
    mssql_update_count = 0
    print(f'sessions false_alarms not matched:\n')
    for session in ci_test_sessions_stat:
        if session['session_id'] not in sessions_id_list_mssql:
            print(session)
            print('')
            return_code += 1
        else:
            if session['false_alarm'] != 'None' and session['false_alarm'] != sessions_id_dict_mssql[session['session_id']]['false_alarm']:
                mssql_update = f"update [GSE_CI].[dbo].[smoke_ci_sessions] set false_alarm='{session['false_alarm']}' where session_id={session['session_id']}"
                mssql_update_commands += mssql_update + '\n'
                mssql_update_count += 1
                print(f"session_id:{session['session_id']}")
                print(f"        WF:{session['false_alarm']}")
                print(f"     MSSQL:{sessions_id_dict_mssql[session['session_id']]['false_alarm']}\n")
                return_code += set_mssql_data(sql_server ,sql_db_name, mssql_update)
    print(f'\ntotal needs update:{mssql_update_count}\n')
    print(mssql_update_commands)
    return return_code
    

def list2dict(dict_list, index_key='id'):
    dict_output = dict()
    for item in dict_list:
        dict_output.update({item[index_key]:item})
    return dict_output

def get_ids(data_dict_list, column_name):
    ids_list = list()
    for item in data_dict_list:
        ids_list.append(item[column_name])
    return ids_list


def set_mssql_data(server, database, query):
    return_code = 0
    global sql_user_pass
    print('sql update:')
    print(query)
    #conn = pyodbc.connect(Driver='{SQL Server}', Server='GKISQL1601.ger.corp.intel.com,3180', Database='vpgci', Trusted_Connection='Yes')
    try:
        if len(sql_user_pass):
            conn = pyodbc.connect(Driver='{SQL Server}', Server=server, Database=database, UID=sql_user_pass[0], PWD=sql_user_pass[1])
        else:
            conn = pyodbc.connect(Driver='{SQL Server}', Server=server, Database=database, Trusted_Connection='Yes')
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        conn.close()
    except pyodbc.DatabaseError as err:
        #raise err
        print(f'\n')
        print(err)
        return_code = 1
    print('---------------------------------------------')
    return return_code  


def get_mssql_data(server, database, query):
    #print(query)
    global sql_user_pass
    #conn = pyodbc.connect(Driver='{SQL Server}', Server='GKISQL1601.ger.corp.intel.com,3180', Database='vpgci', Trusted_Connection='Yes')
    if len(sql_user_pass):
        conn = pyodbc.connect(Driver='{SQL Server}', Server=server, Database=database, UID=sql_user_pass[0], PWD=sql_user_pass[1])
    else:
        conn = pyodbc.connect(Driver='{SQL Server}', Server=server, Database=database, Trusted_Connection='Yes')
    cursor = conn.cursor()
    cursor.execute(query)
    columns = [column[0] for column in cursor.description]
    mssql_data = list()
    for row in cursor.fetchall():
        mssql_data.append(dict(zip(columns, row)))
    #cursor.fetchall()
    return mssql_data


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
    #print(url)
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
        cycle_dict.update({'build_name':cycle['builds'][0]['name']})
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
                    failure_category_set = set()
                    if 'comment' in session['test_session_failure'].keys():
                        comments = str(session['test_session_failure']['comment']).encode('unicode_escape')
                        session_dict.update({'comments':comments.decode().replace("'","").replace('"','')})
                    else:
                        session_dict.update({'comments':'None'})
                    if 'categories' in session['test_session_failure'].keys():
                        for category in session['test_session_failure']['categories']:
                            if category['selected']:
                                failure_category_set.add(category['name'])
                                category_reason_list = list()
                                for reason in category['values']:
                                    if reason['selected']:
                                        # WA for "GTA (WF, RES, TP)" - > "GTA (WF-RES-TP)"
                                        category_reason_list.append(f"{category['name']}:{reason['name'].replace(', ','-')}")
                                if len(category_reason_list) > 0:
                                    failure_reasons_set.add(f"{','.join(category_reason_list)}")
                                else:
                                    failure_reasons_set.add(category['name'])
                    if len(failure_reasons_set) > 0:
                        failure_reasons = str(','.join(failure_reasons_set)).encode('unicode_escape')
                        session_dict.update({'failure_reasons':failure_reasons.decode()})
                        if 'Code Issue' in failure_category_set:
                            session_dict.update({'has_code_issue':True})
                            session_dict.update({'false_alarm':0})
                        else:
                            session_dict.update({'has_code_issue':False})
                            if session['has_regressions'] == True or session['status'] == 'TIMEOUT':
                                session_dict.update({'false_alarm':100})
                            else:
                                session_dict.update({'false_alarm':0})
                    else:
                        session_dict.update({'failure_reasons':'None'})
                        session_dict.update({'has_code_issue':False})
                        session_dict.update({'false_alarm':0})
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

def update_cycles_with_execution_time(ci_cycle_stat, sessions_execution_time_dict):
    for cycle in ci_cycle_stat:
        if cycle['cycle_id'] in sessions_execution_time_dict.keys():
            for key in ['buildEndDateTime']:
                cycle.update({'build_end_date':sessions_execution_time_dict[cycle['cycle_id']][key]})
            for key in ['executionDateTime', 'createTestRunDuration', 'createTestSessionsDuration', 'monitorResultsDuration', 'completeTestRunDuration', 'sendEmailDuration', 'totalDuration']:
                cycle.update({key:sessions_execution_time_dict[cycle['cycle_id']][key]})
        else:
            print(f"{cycle['cycle_id']}") 


def update_sessions_with_tp_data(ci_test_sessions_stat):
    test_plan_dict = get_test_plan_dict(ci_test_sessions_stat)
    for session in ci_test_sessions_stat:
        if session['test_plan_id'] in test_plan_dict.keys():
            session.update({'test_plan_name':get_tp_name(session['test_plan_id'], test_plan_dict)})
            session.update({'environment':get_tp_env(session['test_plan_id'], test_plan_dict)})
        else:
            # for null tp id
            session.update({'test_plan_name':session['label']})
            session.update({'environment':'unknown'})

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

def update_stats(ci_cycle_stat, ci_test_sessions_stat, cycles):
    ci_cycle_stat += get_ci_cycle_stat(cycles)
    ci_test_sessions_stat += get_ci_cycle_session_stat(cycles)
    return 0

def get_gta_data(url, page=None):
    global user_pass
    output = None
    headers = { 'Content-type': 'application/json' }
    if page:
        url += f'&page={page}'
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

def get_date_n_days_ago(days_ago):
    ts = str(datetime.now()- timedelta(days=days_ago))
    return ts[0:10]

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

def check_user_input(user_input):
    try:
        datetime.strptime(user_input, '%Y-%m-%d')
    except ValueError:
        return False
    return True

if __name__ == '__main__':
    user_pass = list()
    sql_user_pass = list()
    ap = argparse.ArgumentParser()
    ap.add_argument('-s', '-status', default='DEFAULT', help='status filter values: [NEW, IN PROGRESS ,COMPLETED, ERROR, TIMEOUT, INCOMPLETE]', required=False)
    ap.add_argument('-i', '-interactive', action='store_true', default=False, help='interactive mode', required=False)
    ap.add_argument('-f', '-date_from', default=get_date_n_days_ago(7), help='date from format yyyy-mm-dd', required=False)
    ap.add_argument('-t', '-date_to', default=get_date_n_days_ago(1), help='date to format yyyy-mm-dd', required=False)
    ap.add_argument('-submitter', default='sys_gtawf', help='submitter default:sys_gtawf', required=False)
    ap.add_argument('-dag', default='CI_SMOKE__gfx-driver__master:gfx-driver__master', help='DAG stream default: CI_SMOKE__gfx-driver__master:gfx-driver__master', required=False)
    ap.add_argument('-upload_only', action='store_true', default=False, help='no cache for gtax api calls (could be use to update cache)', required=False)
    ap.add_argument('-login', default='', help='login', required=False)
    ap.add_argument('-password', default='', help='password', required=False)
    ap.add_argument('-sql_login', default='', help='sql login', required=False)
    ap.add_argument('-sql_password', default='', help='sql password', required=False)
    parsed = ap.parse_args()
    if len(parsed.login) > 1 and len(parsed.password) > 1:
        user_pass.append(parsed.login)
        user_pass.append(parsed.password)
    if len(parsed.sql_login) > 1 and len(parsed.sql_password) > 1:
        sql_user_pass.append(parsed.sql_login)
        sql_user_pass.append(parsed.sql_password)
    date_from = parsed.f
    date_to = parsed.t
    if parsed.i:
        date_from = input(f'provide from date (YYYY-MM-DD) [enter use default={get_date_n_days_ago(7)}]:')
        if not check_user_input(date_from):
            date_from = get_date_n_days_ago(7)
        date_to = input(f'provide to date (YYYY-MM-DD) [enter use default={get_date_n_days_ago(1)}]:')
        if not check_user_input(date_to):
            date_to = get_date_n_days_ago(1)
    main(parsed.s, 100, date_from, date_to, parsed.dag, parsed.submitter, parsed.upload_only)