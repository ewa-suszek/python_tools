import requests
from requests_kerberos import HTTPKerberosAuth
import urllib3
# this is to ignore the ssl insecure warning as we are passing in 'verify=false'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
 
headers = { 'Content-type': 'application/json' }
# Replace the ID here with some article ID
id='1306400485'
id='1707088476'
url = 'https://hsdes-api.intel.com/rest/article/'+id

#url = 'https://hsdes-api.intel.com/rest/article/1306400485/children?tenant=server_rackscale&child_subject=itp_test_case'
response = requests.get(url, verify=False, auth=HTTPKerberosAuth(), headers = headers)

results = response.json()

print(results)

