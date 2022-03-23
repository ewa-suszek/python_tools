'''
HSDES API DOCS: https://hsdes.intel.com/rest/doc/#!/query/getQuery

'''

import requests
from requests_kerberos import HTTPKerberosAuth
import urllib3
# this is to ignore the ssl insecure warning as we are passing in 'verify=false'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
 
headers = { 'Content-type': 'application/json' }
# Replace the ID here with some article ID
id='1808104322'
url = 'https://hsdes-api.intel.com/rest/query/'+id+'?max_results=10000'

response = requests.get(url, verify=False, auth=HTTPKerberosAuth(), headers = headers)

results = response.json()

print(results)

for feature in results['data']:
    print(feature['id'], feature['title'], feature['status'], feature['reason'], feature['release'], feature['owner'], feature['rev'], )


