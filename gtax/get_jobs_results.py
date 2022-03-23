import sys
import os
import argparse
import json
import requests
from datetime import datetime

def main(gtax_instance, job_name, search_type, html=False, action=None):
    job_data = get_jobs_results(gtax_instance, job_name, search_type)
    jobs_passed = list()
    jobs_failed = list()
    jobs_wip = list()
    #job_log_link = ''
    ## to do: log browser 
    # link https://gtax-igk.intel.com/logs/jobs/jobs/0000/3938/39387566/logs/unassigned/0/gfx_ifwi_system_info.txt
    # job_log_file = gfx_ifwi_system_info.txt
    # 
    for job in job_data:
        if job['status'] == 'completed':
            if job['result'] == 'passed':
                jobs_passed.append(job)
            else:
                jobs_failed.append(job)
        else:
            jobs_wip.append(job) 
    print_jobs(gtax_instance, jobs_passed, 'passed')
    print_jobs(gtax_instance, jobs_failed, 'failed')
    print_jobs(gtax_instance, jobs_wip, 'in progress')
    print(f'     passed: {len(jobs_passed)} of {len(job_data)}\n     failed: {len(jobs_failed)} of {len(job_data)}\nin progress: {len(jobs_wip)} of {len(job_data)}\n')
    if html:
        if search_type == 'name':
            gen_html_report(gtax_instance, jobs_passed, jobs_failed, jobs_wip, job_name=job_name)
        else:
            gen_html_report(gtax_instance, jobs_passed, jobs_failed, jobs_wip, job_name=job_data[0]['name'])
    if action:
        gen_action(gtax_instance, jobs_passed, jobs_failed, action)
    return 0

def print_jobs(gtax_instance, jobs_list, title):
    if len(jobs_list) > 0:
        jobs_status_text = '' 
        for job in jobs_list:
            jobs_status_text += f'{job["name"]} {job["client_name"]} {job["status"]} {job["result"]} [{job["submitted_date"]}] [{job["completed_date"]}] https://{gtax_instance}.intel.com/#/clients/{job["client_id"]} http://{gtax_instance}.intel.com/#/jobs/{job["id"]}\n'
        print(f'{title} - {len(jobs_list)}:')
        print(jobs_status_text)

def gen_action(gtax_instance, jobs_passed, jobs_failed, action):
    action_type = action.split('#')[0]
    action_command = action.split('#')[1]
    #if action_type in ['udp', 'setting', 'run_job']:
    if action_type in ['udp']:
        gen_udp_action(gtax_instance, jobs_passed, jobs_failed, action_command)
    else:
        print(f'action {action_type} not defined!')

def gen_udp_action(gtax_instance, jobs_passed, jobs_failed, action_command):
    pass_value = 'Passed'
    fail_value = 'Failed'
    required_flag = ''
    action_command_dict = action_command_to_dict(action_command)
    if 'p_value' in action_command_dict.keys():
        pass_value = action_command_dict['p_value']
    if 'f_value' in action_command_dict.keys():
        fail_value = action_command_dict['f_value']
    if 'req_failed' in action_command_dict.keys():
        if action_command_dict['req_failed'].lower() == 'true':
            required_flag = '-r'
    if 'name' in action_command_dict.keys():
        udp_name = action_command_dict['name']
        action_commands = list()
        if len(jobs_passed) > 0:
            job_name = jobs_passed[0]['name']
            for job in jobs_passed:
                client_id = job["client_id"]
                action_commands.append(f'add_clients_property.exe -i {gtax_instance} -csq "(\'client_id\' = \'{client_id}\' AND \'{udp_name}\' != \'{pass_value}\')" -n {udp_name} -v {pass_value}')
        if len(jobs_failed) > 0:
            job_name = jobs_failed[0]['name']
            for job in jobs_failed:
                client_id = job["client_id"]
                action_commands.append(f'add_clients_property.exe -i {gtax_instance} -csq "(\'client_id\' = \'{client_id}\' AND \'{udp_name}\' != \'{fail_value}\')" -n {udp_name} -v {fail_value} {required_flag}')
        if len(action_commands) > 0:
            save_action_bat(job_name, action_commands)
        else:
            print(f'no completed jobs - action bat not genereted!')    
    else:
        print(f'udp name not defined in the action command: {action_command}') 

def action_command_to_dict(action_command):
    action_command_dict = dict()
    action_command_list = action_command.split('&')
    for command in action_command_list:
        action_command_dict.update({command.split(':')[0]:command.split(':')[1]})
    return action_command_dict

def save_action_bat(job_name, action_commands):
    app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    actions_path = os.path.join(app_path, 'result_check_actions')
    file_name = os.path.join(actions_path, f'action-{job_name}-{get_filename_timestamp()}.bat')
    if not os.path.exists(actions_path):
        os.makedirs(actions_path)
    with open(file_name, 'w') as outfile:
        outfile.write('@echo off\r\n')
        for command in action_commands:
            outfile.write(f'..\{command}\r\n')
        outfile.write('pause\r\n')
    print(f'result action bat saved: {file_name}')
    return 0

def gen_html_report(gtax_instance, jobs_passed, jobs_failed, jobs_wip, job_name):
    if len(jobs_passed) + len(jobs_failed) + len(jobs_wip) > 0:
        app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        html_path = os.path.join(app_path, 'logs_html')
        file_name = os.path.join(html_path, f'{job_name}-{get_filename_timestamp()}.html')
        if not os.path.exists(html_path):
            os.makedirs(html_path)
        with open(file_name, 'w') as outfile:
            outfile.write(html_output(gtax_instance, jobs_passed, jobs_failed, jobs_wip))
        print(f'html log saved: {file_name}')
    return 0

def html_output(gtax_instance, jobs_passed, jobs_failed, jobs_wip):
    job_keys = ['name', 'client_name', 'status', 'result', 'submitted_date', 'completed_date', 'job_link']
    html_output = ''
    html_style = '<style>table {font-family:Verdana;font-size: 10px; border-collapse: collapse;} table, th, td {border: 1px solid black; padding-left: 5px; padding-right: 5px; padding-top: 2px; padding-bottom: 2px;} tr:nth-child(even) {background-color: #f2f2f2;}</style>'
    html_output = f'<!DOCTYPE html><html><head>{html_style}</head><body><div style="overflow-x:auto;"><table><tr>'
    for key in job_keys:
        html_output += f"<th>{key}</th>"
    html_output += f'</tr>'
    for job in jobs_passed:
        html_output += html_output_job(gtax_instance, job, job_keys)
    for job in jobs_failed:
        html_output += html_output_job(gtax_instance, job, job_keys, is_failed=True)
    for job in jobs_wip:
        html_output += html_output_job(gtax_instance, job, job_keys, is_wip=True)
    html_output += '</table></div></body></html>'   
    return html_output

def html_output_job(gtax_instance, job, job_keys, is_failed=False, is_wip=False):
    html_output = '<tr>'
    td_style = ''
    if is_failed:
        td_style = ' style="font-weight:bold; color:#FF0000"'
    if is_wip:
        td_style = ' style="font-weight:bold; color:#0000FF"'
    for key in job_keys:
        if key == 'job_link':
            html_output += f"<td{td_style}><a href='http://{gtax_instance}.intel.com/#/jobs/{job['id']}' target='_blank'>http://{gtax_instance}.intel.com/#/jobs/{job['id']}</a></td>"
        elif key == 'client_name':
            html_output += f"<td{td_style}><a href='http://{gtax_instance}.intel.com/#/clients/{job['client_id']}?tab=properties' target='_blank'>{job['client_name']}</a></td>"
        else:
            html_output += f"<td{td_style}>{job[key]}</td>"
    html_output += '</tr>'
    return html_output

def get_jobs_results(gtax_instance, search_string, search_type='name'):
    jobs_results = list()
    url = None
    if search_type == 'name':
        url = f'http://{gtax_instance}.intel.com/api/v1/jobs?include_tasks=false&include_taskml=false&include_csq=false&include_phases_task_counts=false&full_info=false&{search_type}={search_string}&order_by=id'
    if search_type == 'jobset_session_ids':
        url = f'http://{gtax_instance}.intel.com/api/v1/jobs?include_tasks=false&include_taskml=false&include_csq=false&include_phases_task_counts=false&full_info=false'
        jobset_session_ids = search_string.split(',')
        for session_id in jobset_session_ids:
            url += f'&jobset_session_ids={session_id}'
    if url:
        job_data = get_gtax_data(url)
        for job in job_data['data']:
            if 'completed_date' in job.keys():
                completed_date = job['completed_date']
            else:
                completed_date = '---'
            jobs_results.append({'id':job['id'], 'name':job['name'], 'jobset_session_id':job['jobset_session_id'], 'submitted_date':job['submitted_date'], 'completed_date':completed_date, 'status':job['status'], 'result':job['result'], 'client_id':job['client']['id'], 'client_name':job['client']['name']})
    return jobs_results

def post_gtax_data(url, data):
    headers = { 'Content-type': 'application/json' }
    response = requests.post(url, data, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def get_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    #print(url)
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response.json()

def get_filename_timestamp():
    ts = str(datetime.now())
    ts = ts.replace(':', '_').replace(' ', '-')
    return ts[5:-7]

def log_script_call():
    app_name = os.path.basename(sys.argv[0])
    app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    log_path = os.path.join(app_path, 'logs')
    params_list = sys.argv[1:]
    call_log_file = os.path.join(log_path, f"{app_name.split('.')[0]}_calls.log")
    command = f'{app_name}'
    for param in params_list:
        if param.find(chr(39)) > 0 or param.find(chr(32)) > 0:
            command += f' "{param}"'
        else:
            command += f' {param}'
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    with open(call_log_file, 'a') as log_file:
        log_file.write(f'[{str(datetime.now())}] {command}\n')

if __name__ == '__main__':
    usage_msg = '''get_jobs_results.exe -n thermal_check%% 
       get_jobs_results.exe -n thermal_check%% -i gtax-gcmxd-fm
       get_jobs_results.exe -s 123456 -i gtax-gcmxd-fm -html
       '''
    ap = argparse.ArgumentParser(usage=usage_msg)
    ap.add_argument('-i', '-instance', default='gtax-igk', help='gtax instance:[gtax-igk, gtax-gcmxd-fm, gtax-ril-fm]', required=False)
    ap.add_argument('-n', '-name',  default='', help="job name string")
    ap.add_argument('-s', '-set_session',  default='', help="job set session id")
    ap.add_argument('-a', '-action',  default=None, help="action based on results exp: udp#name:udp_name&p_value:pass_value&f_value:fail_value&req_failed:true")
    ap.add_argument('-html', action='store_true', default=False, help='generate html log', required=False)
    parsed = ap.parse_args()
    #print(parsed)
    log_script_call()
    if not (parsed.n or parsed.s):
        ap.error('\nNo params! Use -n or -s')
    else:
        #print(parsed)
        if parsed.n: 
            main(parsed.i, parsed.n, 'name', html=parsed.html, action=parsed.a)
        if parsed.s: 
            main(parsed.i, parsed.s, 'jobset_session_ids', html=parsed.html, action=parsed.a)
