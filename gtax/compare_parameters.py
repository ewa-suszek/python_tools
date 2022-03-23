
parameters_igk = 'client_name,client_id,client_status,client_is_reserved,bad_do_not_use,bad_gpu_leave_offline,card_ifwi_feature,card_type,carer,eu,gpu_good,gpu_id,gpu_qdf,gpu_stepping,ifwi_tools.asset.dgfx_ifwi,ifwi_tools.asset.dgfx_ifwi.version,ifwi_tools.asset.igfx_ifwi,ifwi_tools.asset.igfx_ifwi.version,kvm,kvm_ip,label_id,linux_capable,location,memory_config,memory_size_above_4gb,netbox_id,owner,p_number,perf_capable,platform,pool,sas,total_physical_memory,unstable_debug_by'
parameters_fm = 'client_name,client_id,client_status,client_is_reserved,_elmo_last_qual_source,_total_qualifier_attempts,cpu_qdf,cpu_qdf_discrete,cpu_stepping,cpu_stepping_discrete,discrete_board_type,discrete_eu_count,discrete_eu_rating,discrete_platform,discrete_socket_type,gtax_allocation,ifwi_tools.asset.dgfx_ifwi,ifwi_tools.asset.dgfx_ifwi.version,lab_notes,media_allocation,not_ddid,platform,platform_shortname,pool,qualifier,rework_cr07,serial_board,serial_board_discrete,serial_cpu,serial_cpu_discrete,serial_sas,serial_sas_discrete,sr_tracking,widi'

parameters_igk_set = set(parameters_igk.split(','))
parameters_fm_set = set(parameters_fm.split(','))

match_params = parameters_igk_set.intersection(parameters_fm_set)

diff_params = parameters_igk_set - parameters_fm_set

diff_params2 = parameters_fm_set - parameters_igk_set

all_params = set()
all_params.update(parameters_igk_set)
all_params.update(parameters_fm_set)

print('match:')
print(match_params)
print(' ')
print(' ')
print(' ')
print('diff:')
print(diff_params)
print(' ')
print(' ')
print(' ')
print('diff2:')
print(diff_params2)