import json
import requests
#http://gtax-gcmxd-fm.intel.com/api/v1/

jobs_id = '35951142'
 
headers = { 'Content-type': 'application/json' }
url = f'http://gtax-gcmxd-fm.intel.com/api/v1/jobs/{jobs_id}?include_task_attributes=true&remove_client_from_taskml=true&full_info=false'

response = requests.get(url, headers = headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })

job_json = response.json()
job_id = job_json['id']
job_name = job_json['name']
job_data = job_json['data']

print(job_id)
print(job_name)
print(json.dumps(job_data))
