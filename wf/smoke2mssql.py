import sys
import math
import pyodbc
import re
import os.path
import argparse
import pickle
import platform
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
    ci_cycle_stat = list()
    ci_test_sessions_stat = list()

    #GETING DATA
    cache_file1_name = f'cycles_master_tmp.cache'
    cache_file2_name = f'sessions_master_tmp.cache'

    if offline_mode and os.path.isfile(cache_file1_name) and os.path.isfile(cache_file2_name):
        with open(cache_file1_name, 'rb') as cache:
            ci_cycle_stat = pickle.load(cache)
        with open(cache_file2_name, 'rb') as cache:
            ci_test_sessions_stat = pickle.load(cache)
    else:
        if dag_stream.find(':') > 0:
            dag_name = dag_stream.split(':')[0]
            stream_name = dag_stream.split(':')[1]
            update_stats(ci_cycle_stat, ci_test_sessions_stat, get_cycles(dag_name, stream_name, submitter, status=status, count=count, date_from=date_from, date_to=date_to))
            print(f'{len(ci_cycle_stat)} cycles and {len(ci_test_sessions_stat)} smoke sessions found')
            #update_cycles_with_execution_time(ci_cycle_stat, get_sessions_execution_time(dag_name, date_from, get_date_n_days_ago(0)))
            update_sessions_with_tp_data(ci_test_sessions_stat)
            update_sessions_with_gtax_data(ci_test_sessions_stat, offline_mode=True)
            with open(cache_file1_name, 'w+b') as cache:
                pickle.dump(ci_cycle_stat, cache) 
            with open(cache_file2_name, 'w+b') as cache:
                pickle.dump(ci_test_sessions_stat, cache)
        else:
            print('wrong dag stream format. use DAG:stream exp: CI_SMOKE__gfx-driver__master:gfx-driver__master')
            return 100
    print(f'uploading cycles')
    return_code += upload_to_mssql('smoke_ci_cycles', ci_cycle_stat)
    print(f'uploading sessions')
    return_code += upload_to_mssql('smoke_ci_sessions', ci_test_sessions_stat)
    return return_code


def get_sessions_execution_time(dag_name, date_from, date_to):
    sessions_execution_time_dict = dict()
    #http://gta.intel.com/api/workflow/v2/statistics/execution_time/_monitored/build_and_operation?dag_id=CI_SMOKE__gfx-driver__master&start=2021-08-01&end=2021-08-24
    url = f'http://gta.intel.com/api/workflow/v2/statistics/execution_time/_monitored/build_and_operation?dag_id={dag_name}&start={date_from}&end={date_to}'
    sessions_execution_time = get_gta_data(url).json()
    if len(sessions_execution_time) > 0:
        for execution_time in sessions_execution_time:
            sessions_execution_time_dict.update({execution_time['testRunId']:execution_time})
    return sessions_execution_time_dict

def upload_to_mssql(table_name, data_list_dict):
    return_code = 0
    table_columns = get_table_columns(get_sql_table_config(table_name))
    print(f'table_name:{table_name}')
    #print(f'columns: {table_columns}')
    insert_data = convert_input_data(table_name, data_list_dict)
    total = len(insert_data)
    print(f'records to upload:{total}')
    count = 0
    for values in insert_data:
        count += 1
        print(f'inserting {count}/{total}', end='\r', flush=True)
        return_code += insert_mssql_data(table_name, table_columns , values)
    print('DONE!                                                                       ')
    return return_code
 

def get_table_columns(sql_table_config):
    data_columns = list()
    for key in sql_table_config.keys():
        data_columns.append(sql_table_config[key]['column_name'])
    return ','.join(data_columns)

def get_list_of_existing_ids(table_name):
    existing_ids = list()
    sql_table_config = get_sql_table_config(table_name)
    response = get_mssql_data(table_name, columns=sql_table_config[1]['column_name'])
    for row in response:
        existing_ids.append(row[sql_table_config[1]['column_name']])
    return existing_ids

def convert_input_data(table_name, input_list_dict, update=False):
    sql_table_config = get_sql_table_config(table_name)
    existing_ids = get_list_of_existing_ids(table_name)
    id_column = sql_table_config[1]['column_name']
    output_data_list = list()
    for data_dict in input_list_dict:
        if data_dict[id_column] not in existing_ids or update == True:
            ## convert list to string with formating base on table config
            temp_string = ''
            for key in sql_table_config.keys():
                if update:
                    temp_string += f'{key} = '
                if str(data_dict[sql_table_config[key]['column_name']]) in ['N', 'None', 'N/A']:
                    temp_string += 'null' + ','
                else:
                    if sql_table_config[key]['data_type'] == 'datetime':
                        if sql_table_config[key]['column_name'] == 'test_plan_timestamp':
                            temp_string += '\'' + str(data_dict[sql_table_config[key]['column_name']]).replace('T', ' ').replace('Z', '')[:-3] + '\','
                        else:
                            temp_string += '\'' + str(data_dict[sql_table_config[key]['column_name']]).replace('T', ' ').replace('Z', '.000') + '\','
                    elif sql_table_config[key]['data_type'] in ['varchar', 'time']:
                        temp_string += '\'' + str(data_dict[sql_table_config[key]['column_name']]) + '\','
                    else:
                        temp_string += str(data_dict[sql_table_config[key]['column_name']]) + ','
            output_data_list.append(temp_string[:-1])
        #else:
            #print(f'{data_dict[id_column]} exist in DB - skipped')
    return output_data_list

def insert_mssql_data(table_name, sql_keys, insert_values, print_only=False):
    return_code = 0
    global sql_user_pass
    global sql_driver
    sql_command = (f"INSERT INTO [dbo].{table_name} ({sql_keys}) \nVALUES ({insert_values});") 
    if print_only:
        print(sql_command)
    else:
        try:
            if len(sql_user_pass):
                conn = pyodbc.connect(Driver=f'{sql_driver}', Server='gksisql017n1.ger.corp.intel.com,3181', Database='GSE_CI', UID=sql_user_pass[0], PWD=sql_user_pass[1])
            else:
                conn = pyodbc.connect(Driver=f'{sql_driver}', Server='gksisql017n1.ger.corp.intel.com,3181', Database='GSE_CI', Trusted_Connection='Yes')
            cursor = conn.cursor()
            cursor.execute(sql_command)
            conn.commit()
            #print("Data Successfully Inserted")   
            conn.close()
        except pyodbc.DatabaseError as err:
            print(sql_command)
            #raise err
            print(f'\n{insert_values} \nnot inserted\n\n')
            print('\n')
            print(err)
            return_code = 1
    return return_code

def update_mssql_data(table_name, id, sql_key_values, print_only=False):
    global sql_user_pass
    global sql_driver
    sql_table_config = get_sql_table_config(table_name)
    id_column = sql_table_config[1]['column_name']
    sql_command = (f"UPDATE [dbo].{table_name} SET {sql_key_values} WHERE {id_column} = {id} ;") 
    if print_only:
        print(sql_command)
    else:
        try:
            if len(sql_user_pass):
                conn = pyodbc.connect(Driver=f'{sql_driver}', Server='gksisql017n1.ger.corp.intel.com,3181', Database='GSE_CI', UID=sql_user_pass[0], PWD=sql_user_pass[1])
            else:
                conn = pyodbc.connect(Driver=f'{sql_driver}', Server='gksisql017n1.ger.corp.intel.com,3181', Database='GSE_CI', Trusted_Connection='Yes')
            cursor = conn.cursor()
            cursor.execute(sql_command)
            conn.commit()
            #print("Data Successfully Inserted")   
            conn.close()
        except pyodbc.DatabaseError as err:
            print(sql_command)
            #raise err
            print(f'\n{sql_key_values} \nnot updated\n\n')
            print(err)
    return 0
    
def get_mssql_data(table_name, columns='all', print_only=False):
    global sql_user_pass
    global sql_driver
    data_list = list()
    if columns == 'all':
        columns = get_table_columns(get_sql_table_config(table_name))
    query = f'select {columns} FROM dbo.{table_name}'
    if print_only:
        print(query)
    else:
        try:
            if len(sql_user_pass):
                conn = pyodbc.connect(Driver=f'{sql_driver}', Server='gksisql017n1.ger.corp.intel.com,3181', Database='GSE_CI', UID=sql_user_pass[0], PWD=sql_user_pass[1], sslverify=0)
            else:
                conn = pyodbc.connect(Driver=f'{sql_driver}', Server='gksisql017n1.ger.corp.intel.com,3181', Database='GSE_CI', Trusted_Connection='Yes')
            cursor = conn.cursor()
            cursor.execute(query)
            row_data = cursor.fetchall()
            conn.close()
            data_list = pyodbc_row_to_dict_list(columns, row_data)
        except pyodbc.DatabaseError as err:
            raise err
    return data_list

def get_sql_driver(driver_select):
    sql_driver = None
    if driver_select:
        sql_driver = driver_select
    else:
        if platform.system() == 'Linux':
            sql_driver = '{ODBC Driver 18 for SQL Server}'
        else:
            sql_driver = '{SQL Server}'
    return sql_driver


def pyodbc_row_to_dict_list(columns, row_data):
    dict_list = list()
    columns_list = columns.split(',')
    for row in row_data:
        temp_dict = dict()
        col = 0
        for column in columns_list:
            temp_dict.update({column: row[col]})
            col += 1
        dict_list.append(temp_dict)
    return dict_list

def get_sql_table_config(table_name):
    sql_table_config = dict()
    tables_dict = dict()
    smoke_ci_cycles_dict = dict()
    smoke_ci_sessions_dict =  dict()
    smoke_ci_cycles_dict.update({1: {'column_name': 'cycle_id', 'data_type': 'int'}})
    smoke_ci_cycles_dict.update({2: {'column_name': 'dag_id', 'data_type': 'varchar'}})
    smoke_ci_cycles_dict.update({3: {'column_name': 'submitter', 'data_type': 'varchar'}})
    smoke_ci_cycles_dict.update({4: {'column_name': 'start_date', 'data_type': 'datetime'}})
    smoke_ci_cycles_dict.update({5: {'column_name': 'status_date', 'data_type': 'datetime'}})
    smoke_ci_cycles_dict.update({6: {'column_name': 'status', 'data_type': 'varchar'}})
    smoke_ci_cycles_dict.update({7: {'column_name': 'cycle_type', 'data_type': 'varchar'}})
    smoke_ci_cycles_dict.update({8: {'column_name': 'label', 'data_type': 'varchar'}})
    smoke_ci_cycles_dict.update({9: {'column_name': 'end_date', 'data_type': 'datetime'}})
    smoke_ci_cycles_dict.update({10: {'column_name': 'duration', 'data_type': 'time'}})
    smoke_ci_cycles_dict.update({11: {'column_name': 'duration_seconds', 'data_type': 'int'}})
    smoke_ci_cycles_dict.update({12: {'column_name': 'stream_name', 'data_type': 'varchar'}})
    smoke_ci_cycles_dict.update({13: {'column_name': 'build_name', 'data_type': 'varchar'}})
    smoke_ci_cycles_dict.update({14: {'column_name': 'build_id', 'data_type': 'int'}})
    smoke_ci_cycles_dict.update({15: {'column_name': 'build_link', 'data_type': 'varchar'}})
    smoke_ci_cycles_dict.update({16: {'column_name': 'build_start_date', 'data_type': 'datetime'}})
    smoke_ci_cycles_dict.update({17: {'column_name': 'started_after_build', 'data_type': 'time'}})
    smoke_ci_cycles_dict.update({18: {'column_name': 'started_after_build_seconds', 'data_type': 'int'}})
    smoke_ci_cycles_dict.update({19: {'column_name': 'lgcb_bad', 'data_type': 'varchar'}})
    smoke_ci_cycles_dict.update({20: {'column_name': 'has_regressions', 'data_type': 'varchar'}})
    smoke_ci_cycles_dict.update({21: {'column_name': 'comparison_view', 'data_type': 'varchar'}})
    smoke_ci_cycles_dict.update({22: {'column_name': 'WW', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({1: {'column_name': 'session_id', 'data_type': 'int'}})
    smoke_ci_sessions_dict.update({2: {'column_name': 'stream_name', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({3: {'column_name': 'build_name', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({4: {'column_name': 'build_id', 'data_type': 'int'}})
    smoke_ci_sessions_dict.update({5: {'column_name': 'build_link', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({6: {'column_name': 'cycle_id', 'data_type': 'int'}})
    smoke_ci_sessions_dict.update({7: {'column_name': 'gtax_id', 'data_type': 'int'}})
    smoke_ci_sessions_dict.update({8: {'column_name': 'label', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({9: {'column_name': 'test_plan_id', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({10: {'column_name': 'test_plan_timestamp', 'data_type': 'datetime'}})
    smoke_ci_sessions_dict.update({11: {'column_name': 'url', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({12: {'column_name': 'gtax_instance', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({13: {'column_name': 'start_date', 'data_type': 'datetime'}})
    smoke_ci_sessions_dict.update({14: {'column_name': 'status_date', 'data_type': 'datetime'}})
    smoke_ci_sessions_dict.update({15: {'column_name': 'status', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({16: {'column_name': 'progress', 'data_type': 'float'}})
    smoke_ci_sessions_dict.update({17: {'column_name': 'remote_name', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({18: {'column_name': 'lgcb_bad', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({19: {'column_name': 'has_notes', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({20: {'column_name': 'has_regressions', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({21: {'column_name': 'has_comment_of_failure_reasons', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({22: {'column_name': 'cycle_type', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({23: {'column_name': 'end_date', 'data_type': 'datetime'}})
    smoke_ci_sessions_dict.update({24: {'column_name': 'duration', 'data_type': 'time'}})
    smoke_ci_sessions_dict.update({25: {'column_name': 'duration_seconds', 'data_type': 'int'}})
    smoke_ci_sessions_dict.update({26: {'column_name': 'duration_min', 'data_type': 'float'}})
    smoke_ci_sessions_dict.update({27: {'column_name': 'comparison_view', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({28: {'column_name': 'WW', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({29: {'column_name': 'test_plan_name', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({30: {'column_name': 'environment', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({31: {'column_name': 'setup_tasks_total', 'data_type': 'int'}})
    smoke_ci_sessions_dict.update({32: {'column_name': 'setup_tasks_success', 'data_type': 'int'}})
    smoke_ci_sessions_dict.update({33: {'column_name': 'setup_success', 'data_type': 'float'}})
    smoke_ci_sessions_dict.update({34: {'column_name': 'test_tasks_total', 'data_type': 'int'}})
    smoke_ci_sessions_dict.update({35: {'column_name': 'test_tasks_worst_success', 'data_type': 'int'}})
    smoke_ci_sessions_dict.update({36: {'column_name': 'test_tasks_best_success', 'data_type': 'int'}})
    smoke_ci_sessions_dict.update({37: {'column_name': 'test_best', 'data_type': 'float'}})
    smoke_ci_sessions_dict.update({38: {'column_name': 'test_worst', 'data_type': 'float'}})
    smoke_ci_sessions_dict.update({39: {'column_name': 'test_best_worst', 'data_type': 'float'}})
    smoke_ci_sessions_dict.update({40: {'column_name': 'max_job_duration', 'data_type': 'float'}})
    smoke_ci_sessions_dict.update({41: {'column_name': 'tpt_met', 'data_type': 'int'}})
    smoke_ci_sessions_dict.update({42: {'column_name': 'failure_reasons', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({43: {'column_name': 'comments', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({44: {'column_name': 'has_code_issue', 'data_type': 'varchar'}})
    smoke_ci_sessions_dict.update({45: {'column_name': 'false_alarm', 'data_type': 'int'}})
    tables_dict.update({'smoke_ci_cycles': smoke_ci_cycles_dict})
    tables_dict.update({'smoke_ci_sessions': smoke_ci_sessions_dict})
    
    if table_name in tables_dict.keys():
        sql_table_config = tables_dict[table_name]
    return sql_table_config

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

def update_sessions_with_gtax_data(ci_test_sessions_stat, offline_mode=False):
    call_count = 0
    call_total = len(ci_test_sessions_stat)
    for session in ci_test_sessions_stat:
        call_count += 1
        if session['gtax_id']:
            print(f'getting gtax data {round(call_count/call_total*100,2)}%   ', end='\r', flush=True)
            jobs_full_info = get_gtax_jobs_full_info(session['gtax_instance'], session['gtax_id'], offline_mode)
            session_task_dict = get_session_tasks_dict(jobs_full_info)
            session_jobs_dict = get_session_jobs_dict(jobs_full_info)
            #TODO
            #add per platform stat (job count jobs time, success rate per platform)

            # init setup success rate
            init_setup_stat = get_gtax_task_stat(session_task_dict, 'setup', submission_type=['init'])
            session.update({'setup_tasks_total':get_stat_key_value(init_setup_stat, 'total')})
            #session.update({'setup_tasks_success':get_stat_key_value(init_setup_stat, 'passed') + get_stat_key_value(init_setup_stat, 'blocked')})
            session.update({'setup_tasks_success':get_stat_key_value(init_setup_stat, 'passed') + get_stat_key_value(init_setup_stat, 'blocked') + get_stat_key_value(init_setup_stat, 'ignored')})
            if session['setup_tasks_total'] > 0:
                session.update({'setup_success':round(session['setup_tasks_success']/session['setup_tasks_total']*100, 2)})
            else:
                session.update({'setup_success':0})
            # test success rate (best-worst)
            init_test_stat = get_gtax_task_stat(session_task_dict, 'test', submission_type=['init'])
            rerun_test_stat = get_gtax_task_stat(session_task_dict, 'test', submission_type=['resume', 'rerun'])
            session.update({'test_tasks_total':get_stat_key_value(init_test_stat, 'total')})
            session.update({'test_tasks_worst_success':get_stat_key_value(init_test_stat, 'passed') + get_stat_key_value(init_test_stat, 'blocked')})
            session.update({'test_tasks_best_success':get_stat_key_value(init_test_stat, 'passed') + get_stat_key_value(rerun_test_stat, 'passed') + get_stat_key_value(init_test_stat, 'blocked')})
            if session['test_tasks_total'] > 0:
                session.update({'test_best':round(session['test_tasks_best_success']/session['test_tasks_total']*100, 2)})
                session.update({'test_worst':round(session['test_tasks_worst_success']/session['test_tasks_total']*100, 2)})
                session.update({'test_best_worst':round((session['test_tasks_best_success']-session['test_tasks_worst_success'])/session['test_tasks_total']*100, 2)})
            else:
                session.update({'test_best':0})
                session.update({'test_worst':0})
                session.update({'test_best_worst':0})
            # max job duration in min.
            max_job_duration = get_max_job_duration(session_jobs_dict)
            session.update({'max_job_duration':max_job_duration})
            session.update({'tpt_met':get_tpt_met(session['duration_min'], 45)})
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
   
def get_gtax_task_stat(session_task_dict, phase, submission_type=[]):
    task_stat_list = list()
    task_status_set = set()
    for task in session_task_dict:
        if session_task_dict[task]['phase'] == phase:
            if len(submission_type) > 0:
                if session_task_dict[task]['submission_type'] in submission_type:
                    task_stat_list.append(session_task_dict[task]['status'])
                    task_status_set.add(session_task_dict[task]['status'])
            else:
                task_stat_list.append(session_task_dict[task]['status'])
                task_status_set.add(session_task_dict[task]['status'])
    task_stat_dict = dict()
    for status in task_status_set:
        task_stat_dict.update({f'{status}':task_stat_list.count(status)})
    task_stat_dict.update({f'total':len(task_stat_list)})
    return(task_stat_dict)

def get_stat_key_value(stat_dict, key, if_not_found=0):
    stat_key_value = if_not_found
    if key in stat_dict.keys():
        stat_key_value = stat_dict[key]
    if not isinstance(stat_key_value, (float, int)):
        stat_key_value = if_not_found
    return stat_key_value
        
def get_session_tasks_dict(session_jobs_data):
    session_task_dict = dict()
    for job_data in session_jobs_data:
        for task_data in job_data['tasks']:
            task_dict = dict()
            for key in ['id', 'job_id', 'task_result_id', 'task_definition_id']:
                task_dict.update({key:task_data[key]})
            if job_data['client']:
                task_dict.update({'client_name':job_data['client']['name']})
                task_dict.update({'client_id':job_data['client']['id']})
            else:
                task_dict.update({'client_name':'unassigned'})
                task_dict.update({'client_id':'unassigned'})
            if 'task_result' in task_data.keys():
                for key in ['submission_type', 'gta_result_key', 'started_date', 'completed_date', 'status', 'gta_status', 'primary_reason', 'publishing_dumps']:
                    if key == 'gta_result_key':
                        task_dict.update({'phase':get_task_phase(task_data['task_result']['gta_result_key'])})
                        task_dict.update({key:task_data['task_result'][key]})
                    else:
                        task_dict.update({key:task_data['task_result'][key]})
            if 'task_definition' in task_data.keys():
                task_dict.update({'command':task_data['task_definition']['command']})
            if 'started_date' in task_dict.keys() and 'completed_date' in task_dict.keys():
                task_dict.update({'duration':get_duration(task_dict['started_date'], task_dict['completed_date'], time_format='%Y-%m-%d %H:%M:%S.%f')})
                task_dict.update({'duration_seconds':get_duration(task_dict['started_date'], task_dict['completed_date'], seconds=True, time_format='%Y-%m-%d %H:%M:%S.%f')})
            session_task_dict.update({task_data['id']:task_dict})
    return session_task_dict

def get_session_jobs_dict(session_jobs_data):
    session_jobs_dict = dict()
    for job_data in session_jobs_data:
        job_dict = dict()
        for key in ['id', 'status', 'name', 'result', 'submission_type', 'submitted_date', 'started_date', 'completed_date', 'duration', 'scheduler_account_name', 'dumps_produced']:
            job_dict.update({key:job_data[key]})
        if 'csq' in job_data.keys():
            csq = job_data['csq']['query']
            job_dict.update({'csq':csq})
            job_dict.update({'platform':get_client_platform(csq)})
            job_dict.update({'pool':get_client_pool(csq)})
        session_jobs_dict.update({job_data['id']:job_dict})
    return session_jobs_dict    

def get_client_platform(csq):
    platform_regex = re.compile(r"('platform' = '.*?')") 
    platform = 'unknown'
    if platform_regex.search(csq):
        platform = platform_regex.search(csq).group(0)[14:-1]
    return platform

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

def get_gtax_jobs_full_info_old(gtax_instance, job_set_session_id, offline_mode=False):
    app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    cache_path = os.path.join(app_path, '_cache')
    cache_file_name = os.path.join(cache_path, f"gtax_{job_set_session_id}_full_info.cache")
    if offline_mode and os.path.isfile(cache_file_name):
        with open(cache_file_name, 'rb') as cache:
            jobs_full_info = pickle.load(cache)
    else:
        #print(f'be patient!! - getting full info of tasks for job set session: {job_set_session_id}')
        url = f'http://{gtax_instance}.intel.com/api/v1/jobs?include_tasks=true&include_csq=true&include_phases_task_counts=true&full_info=true&jobset_session_ids={job_set_session_id}'
        #print(url)
        data = get_gtax_data(url)
        jobs_full_info = data['data']
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        with open(cache_file_name, 'w+b') as cache:
            pickle.dump(jobs_full_info, cache) 
    return jobs_full_info

def get_gtax_jobs_full_info(gtax_instance, job_set_session_id, offline_mode=False):
    app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    cache_path = os.path.join(app_path, '_cache')
    cache_file_name = os.path.join(cache_path, f"gtax_{job_set_session_id}_full_info.gzip")
    if offline_mode and os.path.isfile(cache_file_name):
        jobs_full_info = cache_json_load(cache_file_name)
    else:
        #print(f'be patient!! - getting full info of tasks for job set session: {job_set_session_id}')
        url = f'http://{gtax_instance}.intel.com/api/v1/jobs?include_tasks=true&include_csq=true&include_phases_task_counts=true&full_info=true&jobset_session_ids={job_set_session_id}'
        #print(url)
        data = get_gtax_data(url)
        jobs_full_info = data['data']
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        cache_json_save(jobs_full_info, cache_file_name)
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
    global user_pass
    headers = { 'Content-type': 'application/json' }
    if len(user_pass) == 2:
        response = requests.get(url, auth=HTTPBasicAuth(user_pass[0], user_pass[1]), headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' }, verify=False)
    else:
        response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response.json()

def get_gta_data(url, page=None):
    global user_pass
    output = None
    headers = { 'Content-type': 'application/json' }
    if page:
        url += f'&page={page}'
    if len(user_pass) == 2:
        response = requests.get(url, auth=HTTPBasicAuth(user_pass[0], user_pass[1]), headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' }, verify=False)
    else:
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


def cache_json_save(data, gzip_file_name):
    with gzip.open(gzip_file_name, 'w') as f:
        f.write(json.dumps(data).encode('utf-8')) 
    return 0

def cache_json_load(gzip_file_name):
    with gzip.open(gzip_file_name, 'r') as f:
        data = json.loads(f.read().decode('utf-8'))
    return data

if __name__ == '__main__':
    user_pass = list()
    sql_user_pass = list()
    ts = get_filename_timestamp()
    filename = f'smoke_tpt_report_{ts}.xlsx'
    ap = argparse.ArgumentParser()
    ap.add_argument('-s', '-status', default='DEFAULT', help='status filter values: [NEW, IN PROGRESS ,COMPLETED, ERROR, TIMEOUT, INCOMPLETE]', required=False)
    ap.add_argument('-i', '-interactive', action='store_true', default=False, help='interactive mode', required=False)
    ap.add_argument('-f', '-date_from', default=get_date_n_days_ago(3), help='date from format yyyy-mm-dd', required=False)
    ap.add_argument('-t', '-date_to', default=get_date_n_days_ago(1), help='date to format yyyy-mm-dd', required=False)
    ap.add_argument('-submitter', default='sys_gtawf', help='submitter default:sys_gtawf', required=False)
    ap.add_argument('-dag', default='CI_SMOKE__gfx-driver__master:gfx-driver__master', help='DAG stream default: CI_SMOKE__gfx-driver__master:gfx-driver__master', required=False)
    ap.add_argument('-upload_only', action='store_true', default=False, help='no cache for gtax api calls (could be use to update cache)', required=False)
    ap.add_argument('-login', default='', help='login', required=False)
    ap.add_argument('-password', default='', help='password', required=False)
    ap.add_argument('-sql_login', default='', help='sql login', required=False)
    ap.add_argument('-sql_password', default='', help='sql password', required=False)
    ap.add_argument('-sql_driver', default=None, help='SQL driver name', required=False)
    parsed = ap.parse_args()
    if len(parsed.login) > 1 and len(parsed.password) > 1:
        user_pass.append(parsed.login)
        user_pass.append(parsed.password)
    if len(parsed.sql_login) > 1 and len(parsed.sql_password) > 1:
        sql_user_pass.append(parsed.sql_login)
        sql_user_pass.append(parsed.sql_password)
    sql_driver = get_sql_driver(parsed.sql_driver)
    print(sql_driver)
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
