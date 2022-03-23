
import sys
import os
import argparse
import json
import requests

def get_job_data(file_name):
    with open(file_name, 'r') as f:
        task_ml = f.read()
    return task_ml

def run_gtax_job(gtax_instance, client_id, job_name, job_data):
    data = '{'
    data += f'"job_name": "{job_name}",'
    data += f'"job_data": {job_data},'
    data += f'"client_id": {client_id},'
    data += f'"submitter": "{os.getlogin()}"'
    data += '}'
    print(json.dumps(data))
    status = True
    '''
    response = post_gtax_data(f'http://{gtax_instance}.intel.com/api/v1/jobs', data)
    if response.status_code == 200:
        status = True
    else:
        status = False
        print(response)
    '''
    return status

run_gtax_job('gtax-igk','3817','thermal_check',get_job_data('ifwi_ww49.taskML'))

#print(get_job_data('termal_check.taskML'))
#print(get_job_data('ifwi_ww49.taskML'))

