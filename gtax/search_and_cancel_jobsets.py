import sys
import os.path
import argparse
import json
import requests
from datetime import datetime
import time
import urllib.parse as urlparse
from urllib.parse import parse_qs
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def main(link, gtax_instance, pool, platfrom, user, build, submit_type, root_namespace, os_name, job_status, days_from, notes):
    jobsets_data = None
    instance_dict = {'gtax-shared-fm':'shared', 'gtax-gcmxd-fm':'gcmxd', 'gtax-igk-smoke':'igk_smoke', 'gtax-igk':'igk', 'gtax-igk-presi':'igk_presi', 'gtax-ril.fm':'ril_fm', 'gtax-emu-fm':'emu_fm', 'gtax-sc':'sc', 'gtax-gfxsvlab.fm':'gfxsv_fm_prod', 'gtax-display-ba.iind':'ba_display'}
    if link:
        gtax_instance = get_gtax_instance_from_link(link, instance_dict)
        if gtax_instance:
            jobsets_data = get_jobsets_from_grafana_link(link, days_from)
        else:
            print("no gtax_instance in grafana link!")
    else:
        if gtax_instance in instance_dict.keys():
            jobsets_data = get_jobsets_from_grafana(instance_dict[gtax_instance], pool, platfrom, user, build, submit_type, root_namespace, os_name, job_status, days_from)
        else:
            print(f"no {gtax_instance} instance!\nPlease select one of {str(instance_dict.keys()).replace('dict_keys(','').replace(')','')}")
    if jobsets_data:
        jobsets_list = jobsets_data_2_list(jobsets_data)
        print_jobsets_list(jobsets_list)
        jobsets_ids_list = get_jobsets_ids(jobsets_list)
        print('')
        print('jobsets to cancel:')
        print('')
        are_you_sure = input(f"ARE YOU SURE TO CANCEL LISTED JOBSETS ON {gtax_instance.upper()}? y/n? ") 
        if are_you_sure.lower() == 'y' or are_you_sure.lower() == 'yes':
            print(f'canceling {len(jobsets_ids_list)} jobsets on {gtax_instance}:')
            print_jobsets_ids_list(jobsets_ids_list)
            cancel_jobsets(gtax_instance, jobsets_ids_list, notes)
        else:
            print('aborted!') 
            print('no changes in gtax!') 
    else:
        print('no jobsets to cancel!')
    return 0

def cancel_jobsets(gtax_instance, jobsets_ids_list, notes):
    for jobset_id in jobsets_ids_list:
        print(f'canceling jobset:{jobset_id} on {gtax_instance} with note: {notes}  ', end='')
        if cancel_gtax_jobset(gtax_instance, jobset_id, notes):
            print('- successful')
        else:
            print('false!! not canceled!!')
    return 0    

def get_jobsets_from_grafana(gtax_instance, pool, platfrom, user, build, submit_type, root_namespace, os_name, job_status, days_from):
    jobsets_data = None
    time_now = time.time()
    time_from = time_now - days_from*24*60*60
    url = 'https://gta-monitor.fm.intel.com/api/datasources/proxy/9/_msearch'
    data = '{"search_type":"query_then_fetch","ignore_unavailable":true,"index":"gtax::execution::open_workloads"} {"size":0,"query":{"bool":{"filter":[{"range":{"SubmittedDate":{"gte":'
    data += str(round(time_from * 1000))
    data += ',"lte":'
    data += str(round(time_now * 1000))
    data += ',"format":"epoch_millis"}}},{"query_string":{"analyze_wildcard":true,"query":"*"}}],"must":['
    print('')
    print('geting jobsets for: ', end='')
    grafana_query = list()
    if gtax_instance:
        grafana_query.append(add_query_param('SourceInstance', gtax_instance))
    if pool:
        grafana_query.append(add_query_param('Target.Pool', pool))
    if platfrom:
        grafana_query.append(add_query_param('Target.Platform', platfrom))
    if user:
        grafana_query.append(add_query_param('Submitter', user))
    if build:
        grafana_query.append(add_query_param('GFXDriver.Label', build))
    if submit_type:
        grafana_query.append(add_query_param('SubmissionType', submit_type))
    if root_namespace:
        grafana_query.append(add_query_param('Planning.RootNamespace', root_namespace))
    if os_name:
        grafana_query.append(add_query_param('Target.OSName', os_name))
    if job_status:
        grafana_query.append(add_query_param('JobStatus', job_status))
    data += ','.join(grafana_query)
    data += ']}},"aggs":{"3":{"terms":{"field":"JobsetID","size":5000,"order":{"_count":"desc"},"min_doc_count":1},"aggs":{"4":{"terms":{"field":"Target.Platform","size":500,"order":{"_count":"desc"},"min_doc_count":1},"aggs":{}}}}}}'
    print('')
    print('')
    response = post_grafana_data(url, data)
    if response.status_code == 200:
        jobsets_data = response.json()
    else:
        print(response.status_code)
        print(response.text)
    return jobsets_data

def get_jobsets_from_grafana_link(link, days_from):
    jobsets_data = None
    url = 'https://gta-monitor.fm.intel.com/api/datasources/proxy/9/_msearch'
    grafana_query_params = get_params_from_link(link)
    print('')
    print('geting jobsets for: ', end='')
    time_now = time.time()
    if 'from' in grafana_query_params.keys():
        time_from = time_now - convert_from_sec(grafana_query_params['from'][0])
    else:
        time_from = time_now - days_from*24*60*60
    data = '{"search_type":"query_then_fetch","ignore_unavailable":true,"index":"gtax::execution::open_workloads"} {"size":0,"query":{"bool":{"filter":[{"range":{"SubmittedDate":{"gte":'
    data += str(round(time_from * 1000))
    data += ',"lte":'
    data += str(round(time_now * 1000))
    data += ',"format":"epoch_millis"}}},{"query_string":{"analyze_wildcard":true,"query":"*"}}'
    grafana_query = list()
    if 'var-Filters' in grafana_query_params.keys():
        for query_filter in grafana_query_params['var-Filters']:
            if query_filter.find('|=~|') > 0:
                data += ',{"regexp":{"'
                data += query_filter.split('|=~|')[0]
                data += '":"'
                data += query_filter.split('|=~|')[1]
                data += '"}}'
    data += '],"must":['
    grafana_query = list()
    if 'var-Filters' in grafana_query_params.keys():
        for query_filter in grafana_query_params['var-Filters']:
            if query_filter.find('|=|') > 0:
                grafana_query.append(add_query_param(query_filter.split('|=|')[0], query_filter.split('|=|')[1]))
        data += ','.join(grafana_query)
    grafana_query = list()
    must_not = False
    if 'var-Filters' in grafana_query_params.keys():
        for query_filter in grafana_query_params['var-Filters']:
            if query_filter.find('|!=|') > 0:
                must_not = True
                grafana_query.append(add_query_param(query_filter.split('|!=|')[0], query_filter.split('|!=|')[1], not_match=True))
    if must_not:
        data += '],"must_not":['
        data += ','.join(grafana_query)
    data += ']}},"aggs":{"3":{"terms":{"field":"JobsetID","size":5000,"order":{"_count":"desc"},"min_doc_count":1},"aggs":{"4":{"terms":{"field":"Target.Platform","size":500,"order":{"_count":"desc"},"min_doc_count":1},"aggs":{}}}}}}'
    print('')
    print('')
    response = post_grafana_data(url, data)
    if response.status_code == 200:
        jobsets_data = response.json()
    else:
        print(response.status_code)
        print(response.text)
    return jobsets_data

def get_params_from_link(link):
    parsed = urlparse.urlparse(url=link)
    params_dict = parse_qs(parsed.query)
    return params_dict

def get_gtax_instance_from_link(link, instance_dict):
    gtax_instance = None
    query_instance = None
    params_dict = get_params_from_link(link)
    if 'var-Filters' in params_dict.keys():
        for query_filter in params_dict['var-Filters']:
            if query_filter.split('|=|')[0] == 'SourceInstance':
                query_instance = query_filter.split('|=|')[1]
    for key in instance_dict.keys():
        if instance_dict[key] == query_instance:
            gtax_instance = key
    return gtax_instance

def convert_from_sec(grafana_from):
    from_sec = 7*24*60*60
    from_string = grafana_from.replace('now-','')
    from_value = int(from_string[:-1])
    from_type = from_string[-1]
    if from_type == 'd':
        from_sec = from_value*24*60*60
    elif from_type == 'h':
        from_sec = from_value*60*60
    elif from_type == 'm':
        from_sec = from_value*60
    return from_sec

def add_query_param(param_name, param_value, not_match=False):
        compare_text = '='
        if not_match:
            compare_text = '!='
        query_param = '{"match_phrase":{"'
        query_param += param_name
        query_param += '":{"query":"'
        query_param += param_value
        query_param += '"}}}'
        print(f'{param_name}{compare_text}{param_value}', end=' ')
        return query_param

def add_query_param_regexp(param_name, param_value):
        query_param = '{"regexp":{"'
        query_param += param_name
        query_param += '":"'
        query_param += param_value.replace('\\','\\\\')
        query_param += '"}}'
        print(f'{param_name}={param_value}', end=' ')
        return query_param

def jobsets_data_2_list(jobsets_data):
    jobsets_list = list()
    for bucket in jobsets_data['responses'][0]['aggregations']['3']['buckets']:
        jobsets_list.append({'jobset_id':bucket['key'], 'platform':bucket['4']['buckets'][0]['key'], 'jobs_count':bucket['doc_count']})
    return jobsets_list

def get_jobsets_ids(jobsets_data):
    jobsets_ids = list()
    for jobset in jobsets_data:
        jobsets_ids.append(jobset['jobset_id'])
    return jobsets_ids

def print_jobsets_list(jobsets_list):
    jobs_count = 0
    print(" _________________________________________________ ")
    print("|             |                      |            |")
    print("| {: >11} | {: >20} | {: >10} |".format('jobset_id', 'platform', 'jobs'))
    print("|_____________|______________________|____________|")
    for jobset in jobsets_list:
        jobs_count += jobset['jobs_count']
        print("| {: >11} | {: >20} | {: >10} |".format(jobset['jobset_id'], jobset['platform'], jobset['jobs_count']))
        print("|_____________|______________________|____________|")
    print("|             |                      |            |")
    print("|{: >11}| {: >20} | {: >10} |".format('total jobsets', ' ', 'total jobs'))
    print("|_____________|______________________|____________|")
    print("|             |                      |            |")
    print("| {: >11} | {: >20} | {: >10} |".format(len(jobsets_list), ' ', jobs_count))
    print("|_____________|______________________|____________|")

def print_jobsets_ids_list(jobset_id_list):
    max_col = 19
    col_count = 0
    for i in range(len(jobset_id_list)):
        print(jobset_id_list[i], end=',')
        col_count += 1
        if col_count > max_col:
            print('')
            col_count = 0
    print('')
        
def post_grafana_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.post(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' }, verify=False )
    return response

def cancel_gtax_jobset(gtax_instance, jobset_id, notes):
    url = f'http://{gtax_instance}.intel.com/api/v1/jobsets/{jobset_id}/cancel'
    notes_data = f'"notes": "{notes}"'
    data = '{' + notes_data + '}'
    response = put_gtax_data(url, data)
    if response.status_code == 200:
        status = True
    else:
        status = False
        print(response)
    return status

def put_gtax_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.put(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def delete_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.delete(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def get_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response.json()

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

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-link', default=None, help='grafana link', required=False)
    ap.add_argument('-i', '-instance', default='gtax-igk', help='gtax instance:[gtax-shared-fm, gtax-gcmxd-fm, gtax-igk-smoke, gtax-igk, gtax-igk-presi, gtax-ril.fm, gtax-emu-fm, gtax-sc, gtax-gfxsvlab.fm, gtax-display-ba.iind]', required=False)
    ap.add_argument('-pool', default=None, help='Target Pool', required=False)
    ap.add_argument('-platform', default=None, help='Target Pool', required=False)
    ap.add_argument('-u', '-user', default=None, help='Submitter', required=False)
    ap.add_argument('-b', '-build', default=None, help='GFXDriver.Label', required=False)
    ap.add_argument('-submit_type', default=None, help='SubmissionType', required=False)
    ap.add_argument('-r', '-root_namespace', default=None, help='Planning.RootNamespace', required=False)
    ap.add_argument('-o', '-os_name', default=None, help='Target.OSName', required=False)
    ap.add_argument('-job_status', default=None, help='JobStatus', required=False)
    ap.add_argument('-days_from', default=7, help='days_from', required=False)
    ap.add_argument('-n', '-note', default="canceled by CI team", help='cancel note', required=False)
    parsed = ap.parse_args()
    log_script_call()
    if parsed.link or parsed.pool or parsed.platform or parsed.u or parsed.b or parsed.submit_type or parsed.r or parsed.o or parsed.job_status:
        main(parsed.link, parsed.i, parsed.pool, parsed.platform, parsed.u, parsed.b, parsed.submit_type, parsed.r, parsed.o, parsed.job_status, int(parsed.days_from), parsed.n)
    else:
        print('no search criteria!')
        ap.print_help()
        ap.exit()
    