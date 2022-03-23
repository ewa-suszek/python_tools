import sys
import os
import argparse
import json

#clients = ['GK-DG2-FRD-044', 'GK-DG2-FRD-062', 'GK-DG2-FRD-065', 'GK-DG2-FRD-066', 'GK-DG2-FRD-077', 'GK-DG2-FRD-078', 'GK-DG2-FRD-079', 'GK-DG2-FRD-090', 'GK-DG2-FRD-099', 'GK-DG2-FRD-101', 'GK-DG2-FRD-102', 'GK-DG2-FRD-103', 'GK-DG2-FRD-104', 'GK-DG2-FRD-107', 'GK-DG2-FRD-110', 'GK-DG2-FRD-114']


'GK-CFL-DG2-FRD-087','GK-CFL-DG2-FRD-091','GK-CFL-DG2-FRD-092'

'''
clients = ['GK-DG2-FRD-010', 'GK-DG2-FRD-011', 'GK-DG2-FRD-013', 'GK-DG2-FRD-015', 'GK-DG2-FRD-016', 'GK-DG2-FRD-017', 'GK-DG2-FRD-021', 'GK-DG2-FRD-037', 'GK-DG2-FRD-056', 'GK-DG2-FRD-073', 'GK-DG2-FRD-075', 'GK-DG2-FRD-080', 'GK-DG2-FRD-081', 'GK-DG2-FRD-082', 'GK-DG2-FRD-083', 'GK-DG2-FRD-085', 'GK-DG2-FRD-086', 'GK-DG2-FRD-087', 'GK-DG2-FRD-088', 'GK-DG2-FRD-089', 'GK-DG2-FRD-091', 'GK-DG2-FRD-092', 'GK-DG2-FRD-093', 'GK-DG2-FRD-094']
template_filename = 'cobalt_test_128EU.taskML'
reruns_count = 2
builds_step = 1
'''

'''
driver_from = 7602
driver_to = 7651

asset_name = '-global.asset.driver.asset_name: "master"'
asset_path = '-global.asset.driver.asset_path: "gfx-driver-builds/ci"'
asset_version = '-global.asset.driver.asset_version: "gfx-driver-ci-master-XXXX"'
'''

'''
gfx-driver-ci-comp_igc-12065

gfx-driver-ci-comp_igc-12065
gfx-driver-ci-comp_igc-11959

asset_name = '-global.asset.driver.asset_name: "comp_igc"'
asset_path = '-global.asset.driver.asset_path: "gfx-driver-builds/ci"'
asset_version = '-global.asset.driver.asset_version: "gfx-driver-ci-comp_igc-XXXX"'

'''


'''
driver_from = 8821
driver_to = 8829

asset_name = '-global.asset.driver.asset_name: "master"'
asset_path = '-global.asset.driver.asset_path: "gfx-driver-builds/ci"'
asset_version = '-global.asset.driver.asset_version: "gfx-driver-ci-master-XXXX"'

'''


'''
driver_from = 4208
driver_to = 4210

asset_name = '-global.asset.driver.asset_name: "comp_core"'
asset_path = '-global.asset.driver.asset_path: "gfx-driver-builds/ci"'
asset_version = '-global.asset.driver.asset_version: "gfx-driver-ci-comp_core-XXXX"'
'''

template_filename = '128b0_regression_check_F.taskML'
#clients = 'GK-CFL-DG2-FRD-087','GK-CFL-DG2-FRD-091','GK-CFL-DG2-FRD-092'

clients = 'GK-TGH-DG2-FRD-143', 'GK-TGH-DG2-FRD-147', 'GK-TGH-DG2-FRD-148'

reruns_count = 2
builds_step = 1

driver_from = 12008
driver_to = 12009

asset_name = '-global.asset.driver.asset_name: "comp_igc"'
asset_path = '-global.asset.driver.asset_path: "gfx-driver-builds/ci"'
asset_version = '-global.asset.driver.asset_version: "gfx-driver-ci-comp_igc-XXXX"'

def add_driver_config(template_filename, driver):
    with open(template_filename, 'r') as f:
        template_content = f.read()
    output_file_name = get_output_file_name(template_filename, driver)
    with open(output_file_name, 'w', newline='\r\n') as f:
        f.write(asset_name + '\n')
        f.write(asset_path + '\n')
        f.write(asset_version.replace('XXXX',str(driver)) + '\n')
        f.write(template_content)

def get_output_file_name(template_filename, driver):
    return template_filename.replace('.taskML', f'-{driver}.taskML')

def get_output_test_name(template_filename, driver):
    return template_filename.replace('.taskML', f'-{driver}')

def gen_taskml(taskml_file, driver_from, driver_to, builds_step):
    for driver in range(driver_from, driver_to+1, builds_step):
        add_driver_config(taskml_file, driver)

def gen_test_runs(driver_from, driver_to, template_filename, builds_step):
    client_index = 0
    for reruns in range(reruns_count):
        for driver in range(driver_from, driver_to+1, builds_step):
            print(f'run_job_on_clients.exe -s {clients[client_index]} -n {get_output_test_name(template_filename, driver)} -f {get_output_file_name(template_filename, driver)}')
            client_index += 1
            if client_index >= len(clients):
                client_index = 0
            

gen_taskml(template_filename, driver_from, driver_to, builds_step)
gen_test_runs(driver_from, driver_to, template_filename, builds_step)

jobsets = list()
for i in range(10126292, 10126312):
    jobsets.append(str(i))
print(f'cancel_jobsets.exe -j "{",".join(jobsets)}"')
