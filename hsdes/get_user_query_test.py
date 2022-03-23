'''
HSDES API DOCS: https://hsdes.intel.com/rest/doc/#!/query/getQuery

'''
import os
import sys
import requests
from requests_kerberos import HTTPKerberosAuth
import urllib3
# this is to ignore the ssl insecure warning as we are passing in 'verify=false'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
existing = ['1804665681','1804673188']

def get_user_query_for_subject(user_id, subject_name):
    user_query_dict = dict()
    headers = { 'Content-type': 'application/json' }
    url = 'https://hsdes-api.intel.com/rest/query/MetaData?owner=' + user_id
    response = requests.get(url, verify=False, auth=HTTPKerberosAuth(), headers = headers)
    results = response.json()

    for query in results['data']:
        if query['query.parent_subject_list'] == subject_name:
            user_query_dict.update({query['id']:{'title':query['title'], 'tenant':query['query.parent_tenant_list'], 'subject':query['query.parent_subject_list']}})
    return user_query_dict


queries = get_user_query_for_subject(os.environ['USERNAME'],'bug')

for query in queries:
    if query not in existing:
        print(queries[query]['title'])
    else:
        print('existing')

