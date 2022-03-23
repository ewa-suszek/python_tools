'''
HSDES API DOCS: https://hsdes.intel.com/rest/doc/#!/query/getQuery
'''
import json
import requests
from requests.auth import HTTPBasicAuth
#import urllib3
# this is to ignore the ssl insecure warning as we are passing in 'verify=false'
#urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
 
headers = { 'Content-type': 'application/json' }
# Replace the ID here with some article ID
id='16010909159'
url = 'https://hsdes-api.intel.com/rest/auth/query/'+id+'?max_results=10000'
user = 'jwojcik'
token = 'K4ID3nnDUIwkI7Gy2Fobw9VlzsExuVHVKk3+OnqrDOobJ1S8='
response = requests.get(url, verify=False, auth=HTTPBasicAuth(user, token), headers = headers)

results = response.json()
with open('hsdes_results.json', 'w+') as results_file:
    results_file.write(json.dumps(results))

print(results['total'])



