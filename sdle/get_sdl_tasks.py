import requests
import urllib3
import json
# this is to ignore the ssl insecure warning as we are passing in 'verify=false'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

 
headers = {'Authorization': 'Token 981050d9b8eba8ef73509451e4b42563b63d17bf'}
# SDL PROJECT ID
# 1145 - DMP
# 842 - PSMS
# 102 - RSD 2.4
# 1389 - PSME -SIM
# 1973 - ICO
# 198 - Workload Collector
# 2399 Performance Framework

id='1973'

url = 'https://sdp-prod.intel.com/api/v2/projects/'+id+'/tasks/?include=tags&expand=status,tags'

response = requests.get(url, verify=False, headers=headers)

json.all_tasks = response.json()

phase_dict = {"CX1":"Project Management","X1":"Requirements","X2":"Architecture & Design","X3":"Development","X4":"Testing","X5":"Deployment"}
sdl_tasks = []
sdl_statuses = []

for task in json.all_tasks['results']:
   sdl_tasks.append([task['task_id'],task['title'],task['status']['name'],phase_dict.get(task['phase']),task['priority'],task['tags']['library_tags']])
   sdl_statuses.append(task['status']['name'])

sdl_tasks.sort()

print('--------------------------------------------------------------------------------------------------------------------')
print('--   PreprodComplete   ---------------------------------------------------------------------------------------------')
print('--------------------------------------------------------------------------------------------------------------------')
for task in sdl_tasks:
   if 'PreprodComplete' in task[5]:
      print(f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]};{task[5]}")

print('--------------------------------------------------------------------------------------------------------------------')
print('--   PreprodInprogress   -------------------------------------------------------------------------------------------')
print('--------------------------------------------------------------------------------------------------------------------')

for task in sdl_tasks:
   if 'PreprodInprogress' in task[5]:
      print(f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]};{task[5]}")

print('--------------------------------------------------------------------------------------------------------------------')

for task in sdl_tasks:
   if 'PreprodInprogress' not in task[5] and 'PreprodComplete' not in task[5]:
      print(f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]};{task[5]}")
   
print('--------------------------------------------------------------------------------------------------------------------')  

print(f"      Incomplete:{sdl_statuses.count('Incomplete')} - {round(sdl_statuses.count('Incomplete')/len(sdl_statuses)*100,2)}%") 
print(f"     In Progress:{sdl_statuses.count('In Progress')} - {round(sdl_statuses.count('In Progress')/len(sdl_statuses)*100,2)}%") 
print(f"  Not Applicable:{sdl_statuses.count('Not Applicable')} - {round(sdl_statuses.count('Not Applicable')/len(sdl_statuses)*100,2)}%") 
print(f"        Complete:{sdl_statuses.count('Complete')} - {round(sdl_statuses.count('Complete')/len(sdl_statuses)*100,2)}%") 
print(f"           Total:{len(sdl_statuses)}") 
print(f"Total Applicable:{len(sdl_statuses)-sdl_statuses.count('Not Applicable')}") 
print(f"  Complete + N/A:{sdl_statuses.count('Complete')+sdl_statuses.count('Not Applicable')} - {round((sdl_statuses.count('Complete')+sdl_statuses.count('Not Applicable'))/len(sdl_statuses)*100,2)}%")
print(f"          Target:{round(len(sdl_statuses)*.75,0)} - 75%")

