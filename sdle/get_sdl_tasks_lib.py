import requests
import urllib3
import json
# this is to ignore the ssl insecure warning as we are passing in 'verify=false'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
headers = {'Authorization': 'Token 981050d9b8eba8ef73509451e4b42563b63d17bf'}

# all tags list: https://sdp-prod.intel.com/api/v2/tags/
# tags: PreprodComplete PreprodInprogress SWPCLS SWS4 Evidence DEPRECATED


url = 'https://sdp-prod.intel.com/api/v2/library/tasks/?include=verification_coverage,categories,tags,amendments'

response = requests.get(url, verify=False, headers=headers)

json.all_tasks = response.json()

phase_dict = {"CX1":"Project Management","X1":"Requirements","X2":"Architecture & Design","X3":"Development","X4":"Testing","X5":"Deployment"}
sdl_tasks = []
sdl_pre_prod_complete = []
sdl_pre_prod_in_progress = []
sdl_evidence = []
sdl_sws4 = []
sdl_deprecated = []


for task in json.all_tasks['results']:
   sdl_tasks.append([task['id'],task['title'],phase_dict.get(task['phase']),task['priority'],task['tags']])

sdl_tasks.sort()

print('--------------------------------------------------------------------------------------------------------------------')
print('--   PreprodComplete   ---------------------------------------------------------------------------------------------')
print('--------------------------------------------------------------------------------------------------------------------')
for task in sdl_tasks:
   if 'PreprodComplete' in task[4]:
      sdl_pre_prod_complete.append(task[0])
      print(f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]}")

print('--------------------------------------------------------------------------------------------------------------------')
print('--   PreprodInprogress   -------------------------------------------------------------------------------------------')
print('--------------------------------------------------------------------------------------------------------------------')

for task in sdl_tasks:
   if 'PreprodInprogress' in task[4]:
      sdl_pre_prod_in_progress.append(task[0])
      print(f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]}")

print('--------------------------------------------------------------------------------------------------------------------')
print('--   SWS4   -------------------------------------------------------------------------------------------')
print('--------------------------------------------------------------------------------------------------------------------')

for task in sdl_tasks:
   if 'SWS4' in task[4] and 'PreprodInprogress' not in task[4] and 'PreprodComplete' not in task[4]:
      sdl_sws4.append(task[0])
      print(f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]}")
      
print('--------------------------------------------------------------------------------------------------------------------')
print('--   Evidence   ----------------------------------------------------------------------------------------------------')
print('--------------------------------------------------------------------------------------------------------------------')


for task in sdl_tasks:
   if 'Evidence' in task[4]:
      sdl_evidence.append(task[0])
      print(f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]}")

print('--------------------------------------------------------------------------------------------------------------------')
print('--   DEPRECATED   --------------------------------------------------------------------------------------------------')
print('--------------------------------------------------------------------------------------------------------------------')

for task in sdl_tasks:
   if 'DEPRECATED' in task[4]:
      sdl_deprecated.append(task[0])
      print(f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]}")

print('--------------------------------------------------------------------------------------------------------------------')  


print(f"  PreprodComplete:{len(sdl_pre_prod_complete)}") 
print(f"PreprodInprogress:{len(sdl_pre_prod_in_progress)}") 
print(f"             SWS4:{len(sdl_sws4)}") 
print(f"         Evidence:{len(sdl_evidence)}") 
print(f"       DEPRECATED:{len(sdl_deprecated)}") 
print(f"            Total:{len(sdl_tasks)}") 

