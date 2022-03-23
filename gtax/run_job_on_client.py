import json
import requests
#http://gtax-gcmxd-fm.intel.com/api/v1/

job_id = '35951142'
client_name = 'FM-ICT-018'
 
headers = { 'Content-type': 'application/json' }
url = f'http://gtax-gcmxd-fm.intel.com/api/v1/jobs/{job_id}?include_task_attributes=true&remove_client_from_taskml=true&full_info=false'

response = requests.get(url, headers = headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })

job_json = response.json()
job_name = job_json['name']
job_data = job_json['data']

new_job_data = {'name': job_name, 'job_data': json.dumps(job_data), 'target_client': client_name}

""" 
{
  "job_name": "string",
  "job_data": "string",
  "target_client": "string",
  "client_name": "string",
  "client_id": 0,
  "submitter": "string"
}
 """

#print(job_name)
#print(json.dumps(job_data))
print(new_job_data)

#url = 'http://gtax-gcmxd-fm.intel.com/api/v1/jobs'

