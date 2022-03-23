import requests
import urllib3
import json
# this is to ignore the ssl insecure warning as we are passing in 'verify=false'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

 
headers = {'Authorization': 'Token 981050d9b8eba8ef73509451e4b42563b63d17bf'}
# SDL PROJECT ID
# 1145 - DMP
# 842 - PSMS
id='1145'

url = 'https://sdp-prod.intel.com/api/v2/projects/'+id+'/?include=permissions,task_counts,incomplete_tasks'

response = requests.get(url, verify=False, headers=headers)

json.all_tasks = response.json()


print(response.json())



