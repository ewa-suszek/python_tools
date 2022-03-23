# 
#  HSDES API: https://hsdes.intel.com/rest/doc/
#
import requests
from requests_kerberos import HTTPKerberosAuth
import urllib3
import json    

    
# this is to ignore the ssl insecure warning as we are passing in 'verify=false'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_query(query_id):
    headers = {'Content-type':'application/json'}
    url = f'https://hsdes-api.intel.com/rest/query/{query_id}'
    response = requests.get(url, verify=False, auth=HTTPKerberosAuth(), headers=headers)
    results = response.json()
    return results['data']


query_data = []
query_data = get_query(18010329045)

print(len(query_data))

print(query_data[0])


