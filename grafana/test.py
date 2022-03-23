
import sys
import os.path
import argparse
import json
import requests
from datetime import datetime
from datetime import timedelta
import time


'''
url:"api/datasources/proxy/9/_msearch"
method:"POST"
data:"{"search_type":"query_then_fetch","ignore_unavailable":true,"index":"gtax::execution::open_workloads"} {"size":0,"query":{"bool":{"filter":[{"range":{"SubmittedDate":{"gte":1611319981107,"lte":1611924781107,"format":"epoch_millis"}}},{"query_string":{"analyze_wildcard":true,"query":"*"}}],"must":[{"match_phrase":{"SourceInstance":{"query":"igk"}}},{"match_phrase":{"Target.Pool":{"query":"CI_DG2"}}},{"match_phrase":{"GFXDriver.Label":{"query":"gfx-driver-ci-master-7095"}}}]}},"aggs":{"3":{"terms":{"field":"JobsetID","size":500,"order":{"_count":"desc"},"min_doc_count":1},"aggs":{"4":{"terms":{"field":"Target.Platform","size":500,"order":{"_count":"desc"},"min_doc_count":1},"aggs":{}}}}}} "


data:"{"search_type":"query_then_fetch","ignore_unavailable":true,"index":"gtax::execution::open_workloads"}{"size":10000,"query":{"bool":{"filter":[{"range":{"SubmittedDate":{"gte":1611321838636,"lte":1611926638636,"format":"epoch_millis"}}},{"query_string":{"analyze_wildcard":true,"query":"*"}}],"must":[{"match_phrase":{"SourceInstance":{"query":"igk"}}},{"match_phrase":{"Target.Pool":{"query":"CI_DG2"}}},{"match_phrase":{"GFXDriver.Label":{"query":"gfx-driver-ci-master-7095"}}},{"match_phrase":{"JobStatus":{"query":"new"}}},{"match_phrase":{"Target.Platform":{"query":"DG2"}}},{"match_phrase":{"Target.OSName":{"query":"Windows 20H2 Vibranium x64"}}},{"match_phrase":{"SubmissionType":{"query":"init"}}},{"match_phrase":{"Planning.RootNamespace":{"query":"/render/tp/ci_daily/mainline"}}}]}},"sort":{"SubmittedDate":{"order":"desc","unmapped_type":"boolean"}},"script_fields":{}} "

url:"api/datasources/proxy/9/_msearch"
method:"POST"
data:"{"search_type":"query_then_fetch","ignore_unavailable":true,"index":"gtax::execution::open_workloads"} {"size":0,"query":{"bool":{"filter":[{"range":{"SubmittedDate":{"gte":1611333426653,"lte":1611938226653,"format":"epoch_millis"}}},{"query_string":{"analyze_wildcard":true,"query":"*"}}],"must":[{"match_phrase":{"SourceInstance":{"query":"igk"}}},{"match_phrase":{"Target.Pool":{"query":"CI_SKL"}}},{"match_phrase":{"Submitter":{"query":"sys_gtawf"}}}]}},"aggs":{"3":{"terms":{"field":"GFXDriver.Label","size":15,"order":{"_count":"desc"},"min_doc_count":2},"aggs":{"2":{"date_histogram":{"interval":"5m","field":"SubmittedDate","min_doc_count":0,"extended_bounds":{"min":1611333426653,"max":1611938226653},"format":"epoch_millis"},"aggs":{}}}}}} "

data:"{"search_type":"query_then_fetch","ignore_unavailable":true,"index":"gtax::execution::open_workloads"} {"size":0,"query":{"bool":{"filter":[{"range":{"SubmittedDate":{"gte":1611323065268,"lte":1611927865268,"format":"epoch_millis"}}},
{"query_string":{"analyze_wildcard":true,"query":"*"}}],
"must":[
    {"match_phrase":{"SourceInstance":{"query":"igk"}}},
    {"match_phrase":{"Target.Pool":{"query":"CI_DG2"}}},
    {"match_phrase":{"GFXDriver.Label":{"query":"gfx-driver-ci-master-7095"}}},
    {"match_phrase":{"JobStatus":{"query":"new"}}},
    {"match_phrase":{"Target.Platform":{"query":"DG2"}}},
    {"match_phrase":{"Target.OSName":{"query":"Windows 20H2 Vibranium x64"}}},
    {"match_phrase":{"SubmissionType":{"query":"init"}}},
    {"match_phrase":{"Planning.RootNamespace":{"query":"/render/tp/ci_daily/mainline"}}}]
    }},"aggs":{"3":{"terms":{"field":"JobsetID","size":500,"order":{"_count":"desc"},"min_doc_count":1},"aggs":{"4":{"terms":{"field":"Target.Platform","size":500,"order":{"_count":"desc"},"min_doc_count":1},"aggs":{}}}}}}"
'''

#url = 'https://gta-monitor.fm.intel.com/api/datasources/proxy/9/_msearch'
#data = '{"search_type":"query_then_fetch","ignore_unavailable":true,"index":"gtax::execution::open_workloads"} {"size":0,"query":{"bool":{"filter":[{"range":{"SubmittedDate":{"gte":1611319981107,"lte":1611924781107,"format":"epoch_millis"}}},{"query_string":{"analyze_wildcard":true,"query":"*"}}],"must":[{"match_phrase":{"SourceInstance":{"query":"igk"}}},{"match_phrase":{"Target.Pool":{"query":"CI_DG2"}}},{"match_phrase":{"GFXDriver.Label":{"query":"gfx-driver-ci-master-7095"}}}]}},"aggs":{"3":{"terms":{"field":"JobsetID","size":500,"order":{"_count":"desc"},"min_doc_count":1},"aggs":{"4":{"terms":{"field":"Target.Platform","size":500,"order":{"_count":"desc"},"min_doc_count":1},"aggs":{}}}}}}'


def get_jobsets_from_grafana(gta_instance=None, pool=None, platfrom=None, user=None, build=None, submit_type=None, root_namespace=None, os_name=None, job_status=None, days_from=7):
    jobsets_data = None
    time_now = time.time()
    time_from = time_now - days_from*24*60*60
    url = 'https://gta-monitor.fm.intel.com/api/datasources/proxy/9/_msearch'
    data = '{"search_type":"query_then_fetch","ignore_unavailable":true,"index":"gtax::execution::open_workloads"} {"size":0,"query":{"bool":{"filter":[{"range":{"SubmittedDate":{"gte":'
    data += str(round(time_from * 1000))
    data += ',"lte":'
    data += str(round(time_now * 1000))
    data += ',"format":"epoch_millis"}}},{"query_string":{"analyze_wildcard":true,"query":"*"}}],"must":['
    grafana_query = list()
    if gta_instance:
        grafana_query.append(add_query_param('SourceInstance', gta_instance))
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
    response = post_grafana_data(url, data)
    if response.status_code == 200:
        jobsets_data = response.json()
    else:
        print(response.status_code)
        print(response.text)
    return jobsets_data

def add_query_param(param_name, param_value):
        query_param = '{"match_phrase":{"'
        query_param += param_name
        query_param += '":{"query":"'
        query_param += param_value
        query_param += '"}}}'
        return query_param

def jobsets_data_2_list(jobsets_data):
    jobsets_list = list()
    for bucket in jobsets_data['responses'][0]['aggregations']['3']['buckets']:
        jobsets_list.append({'jobset_id':bucket['key'], 'platform':bucket['4']['buckets'][0]['key'], 'jobs_count':bucket['doc_count']})
    return jobsets_list

def get_jobsets_ids(jobsets_data):
    jobsets_ids = list()
    for jobset in jobsets_list:
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

def post_grafana_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.post(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' }, verify=False )
    return response

#jobsets_data = get_jobsets_from_grafana(gta_instance='igk', user='sys_gtawf', pool='CI_DG2')
#jobsets_data = get_jobsets_from_grafana(gta_instance='igk', user='sys_gtawf')
#jobsets_list = jobsets_data_2_list(jobsets_data)
#print_jobsets_list(jobsets_list)
#print('=============================================================')
#print(jobsets_data['responses'])
#print('=============================================================')
#print(jobsets_data['responses'][0]['aggregations']['3']['buckets'])

instance_dict = {'gtax-shared-fm':'shared', 'gtax-gcmxd-fm':'gcmxd', 'gtax-igk-smoke':'igk_smoke', 'gtax-igk':'igk', 'gtax-igk-presi':'igk_presi', 'gtax-ril.fm':'ril_fm', 'gtax-emu-fm':'emu_fm', 'gtax-sc':'sc', 'gtax-gfxsvlab.fm':'gfxsv_fm_prod', 'gtax-display-ba.iind':'ba_display'}

print(str(instance_dict.keys()).replace('dict_keys(','').replace(')',''))
