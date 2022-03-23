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


dags = get_gta_data('http://gta.intel.com/api/workflow/v2/dags').json()

print(len(dags))

dag_count = 0
dag_filter_list = list()

for dag in dags:
    if dag['dag_id'].find('CI_DAILY_') == 0 and dag['dag_id'].lower().find('presi') < 0 and dag['dag_id'].lower().find('smoke') < 0  and dag['dag_id'].lower().find('emulation') < 0 and str(dag['schedule']).find('* * *') >0:
        dag_count += 1
        dag_filter_list.append(dag['dag_id'])
        print(f"python get_wf_data_for_dags.py -dag {dag['dag_id']}")
        #print(dag)

print(','.join(dag_filter_list))
print(dag_count)
