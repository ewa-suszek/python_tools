import json
import requests
import argparse

#http://gtax-gcmxd-fm.intel.com/api/v1/

def get_gtax_data(url):
    headers = { 'Content-type': 'application/json' }
    response = requests.get(url, headers=headers, proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    return response

def get_job_properties(gtax_instance, job_id):
    properties = dict()
    hw_config_file = 'hwconfig_before_task.json'
    hw_config_file = 'hwconfig_after_task.json'
    if job_id:
        log_sub_folder = ('0000' + job_id)[-8:-4]
        #todo check link
        # old was: /logs/tests/0/hwconfig_before_task.json
        #http://gtax-igk.intel.com/api/v1/jobs/41425181?full_info=true
        #http://gtax-gcmxd-fm.intel.com/api/v1/jobs/39654922?full_info=true
        if gtax_instance == 'gtax-igk':
            #log_link = f'http://{gtax_instance}.intel.com/logs/jobs/jobs/0000/{log_sub_folder}/{job_id}/logs/test/1/{hw_config_file}'
            log_link = f'http://{gtax_instance}.intel.com/logs/jobs/jobs/0000/{log_sub_folder}/{job_id}/logs/tests/0/{hw_config_file}'
        else:
            log_link = f'http://{gtax_instance}.intel.com/logs/jobs/jobs/0000/{log_sub_folder}/{job_id}/logs/tests/0/{hw_config_file}'
        print(f'getting hwconfig_before_task log for job id {job_id} form {log_link}')
        response = get_gtax_data(log_link)
        if response.status_code == 200:
            properties = response.json()
        else:
            print(f'[WARNING!] no hwconfig_before_task.json for {job_id} (response code:{response.status_code})')
            properties.update({'client_id': ''})
            properties.update({'client_name': 'unassigned'})
        properties.update({'job_id': job_id})
        properties.update({'gtax_instance': gtax_instance})
    return properties

def get_jobs_properties(jobs_list):
    jobs_properties_list = []
    for job_id_instance in jobs_list:
        job_id = job_id_instance.split(':')[1]
        gtax_instance = job_id_instance.split(':')[0]
        jobs_properties_list.append(get_job_properties(gtax_instance, job_id))
    return jobs_properties_list


def get_job_data(gtax_instance, job_id):
    job_dict = dict()
    url = f'http://{gtax_instance}.intel.com/api/v1/jobs/{job_id}'
    print(f'getting job data for job id {job_id} form {url}')
    response = get_gtax_data(url)
    if response.status_code == 200:
        job_dict = response.json()
    else:
        print(f'[WARNING!] no data for {job_id} (response code:{response.status_code})')
        job_dict.update({'id': job_id})
        for key in ['name', 'status', 'result','submission_type']:
            job_dict.update({key: 'no job data'})
    return job_dict

def get_jobs_data(jobs_list):
    jobs_data_list = list()
    for job_id_instance in jobs_list:
        job_id = job_id_instance.split(':')[1]
        gtax_instance = job_id_instance.split(':')[0]
        job_data = get_job_data(gtax_instance, job_id)
        job_dict = dict()
        for key in ['id', 'name', 'status', 'result','submission_type']:
            if key in job_data.keys():
                job_dict.update({key:job_data[key]})
        job_dict.update({'gtax_instance':gtax_instance})
        jobs_data_list.append(job_dict)
    return jobs_data_list


def get_all_jobs_keys(job_properties_list):
    keys_set = set()
    for job_properties in job_properties_list:
        if job_properties:
            for key in job_properties.keys():
                keys_set.add(key)
    return sorted(keys_set)

def print_keys_to_html(key, jobs_property_values):
    html_text = f'<tr><td style="font-weight: bold;">{key}</td>'
    for job_property_value in jobs_property_values:
        html_text += f'<td>{job_property_value}</td>'
    html_text += f'</tr>'
    return html_text

def check_all_not_equal(jobs_property_values):
    values_set = set()
    for job_property_value in jobs_property_values:
        values_set.add(job_property_value)
    if len(values_set) == 1:
        all_not_equal = False
    else:
        all_not_equal = True
    return all_not_equal

def html_output_keys(job_properties_list, keys_set, diff_mode='diff'):
    html_output = ''
    for key in sorted(keys_set):
        jobs_property_values = []
        for job_properties in job_properties_list:
            if key in job_properties.keys():
                jobs_property_values.append(job_properties[key])
            else:
                jobs_property_values.append(None)
        if diff_mode == 'diff' or diff_mode == 'match':
            if check_all_not_equal(jobs_property_values) and diff_mode == 'diff':
                html_output += print_keys_to_html(key, jobs_property_values)
            if not check_all_not_equal(jobs_property_values) and diff_mode == 'match':
                html_output += print_keys_to_html(key, jobs_property_values)               
        else:
            html_output += print_keys_to_html(key, jobs_property_values)
    return html_output

def html_output_jobs_data(jobs_data_list):
    html_output = ''
    for key in get_all_jobs_keys(jobs_data_list):
        html_output += f'<tr><td style="font-weight: bold; text-align: left; color: #800080; background-color:#DDDDDD;">job {key}</td>'
        for job in jobs_data_list:
            status_color = get_color_for_status(job['result'])
            if key == 'id':
                gtax_instance = job['gtax_instance']
                html_output += f'<td style="font-weight: bold; text-align: center; color: #800080; background-color:{status_color};"><a href="http://{gtax_instance}.intel.com/#/jobs/{job[key]}" target="_blank">{job[key]}</a></td>'
            else:
                html_output += f'<td style="font-weight: bold; text-align: center; color: #800080; background-color:{status_color};">{job[key]}</td>'
        html_output += f'</tr>'
    return html_output

def get_color_for_status(job_status):
    status_color = '#DDDDDD'
    if job_status == 'failed':
        status_color = '#FFCCCB'
    if job_status == 'passed':
        status_color = '#90EE90'
    return status_color


def main(gtax_instance, jobs_string, diff_mode, output_file_name):
    jobs_list = list()
    if jobs_string.find(':') > 0:
        # if job list with instance seperated by :
        # gtax-igk:41425181,41425197;gtax-sc:41425181,41425197
        jobs_instance_list = jobs_string.split(';')
        for job_instance in jobs_instance_list:
            instance = job_instance.split(':')[0]
            jobs = job_instance.split(':')[1]
            for job in jobs.split(','):
                jobs_list.append(f'{instance}:{job}')
    else:
        # assume all jobs on the same instance
        jobs_no_instance_list = jobs_string.split(',')
        for job_no_instance in jobs_no_instance_list:
            jobs_list.append(f'{gtax_instance}:{job_no_instance}')

    print(f'jobs to compare: {jobs_list}')
    jobs_data_list = get_jobs_data(jobs_list)
    jobs_properties_list = get_jobs_properties(jobs_list)
    all_keys_set = get_all_jobs_keys(jobs_properties_list)
    html_output = ''
    html_style = '<style>table {font-family:Verdana;font-size: 10px; border-collapse: collapse; width:100%;} table, th, td {border: 1px solid black;} tr:nth-child(even) {background-color: #f2f2f2;}</style>'
    html_output = f'<!DOCTYPE html><html><head>{html_style}</head><body><div style="overflow-x:auto;"><table><tr><th>property</th>'
    for job in jobs_properties_list:
        html_output += f"<th><a href='http://{job['gtax_instance']}.intel.com/#/clients/{job['client_id']}?tab=properties' target='_blank'>{job['client_name']}</a></th>"
    html_output += f'</tr>'
    html_output += html_output_jobs_data(jobs_data_list)
    html_output += html_output_keys(jobs_properties_list, all_keys_set, diff_mode)
    html_output += '</table></div></body></html>'
    html_file = open(output_file_name, "w")
    html_file.write(html_output)
    html_file.close()
    return 0

if __name__ == '__main__':
    usage_msg = '''compare_config_for_jobs.exe -j "37212164,37234763"
       compare_config_for_jobs.exe -j "37212164,37234763" -i gtax-gcmxd-fm
       compare_config_for_jobs.exe -j "37212164,37234763" -i gtax-gcmxd-fm -m match
       compare_config_for_jobs.exe -j "37212164,37234763" -i gtax-gcmxd-fm -o my_output_file_name.html
       optional with instance:
       ; - instance with jobs separator
       : - instance and jobs separator
       instance1:job1_id,job2_id;instance2:job3_id,job4_id
       compare_config_for_jobs.exe -j "gtax-igk:41425181,41425197;gtax-gcmxd-fm:37212164,37234763"'''
    ap = argparse.ArgumentParser(usage=usage_msg)
    ap.add_argument('-i', '-instance', default='gtax-igk', help='gtax instance:[gtax-igk, gtax-gcmxd-fm]', required=False)
    ap.add_argument('-j', '-jobs', help='jobs list (optional with instance): "gtax-igk:41425181,41425197;gtax-gcmxd-fm:37212164,37234763"', required=True)
    ap.add_argument('-m', '-mode', default='diff', choices=['diff', 'match', 'all'], help='diff mode: [diff, match, all]', required=False)
    ap.add_argument('-o', '-output', default='jobs_diff_output.html', help='output file name: jobs_diff_output.html', required=False)
    parsed = ap.parse_args()
    #print(parsed)
    if parsed.j:
        main(parsed.i, parsed.j, parsed.m, parsed.o)


