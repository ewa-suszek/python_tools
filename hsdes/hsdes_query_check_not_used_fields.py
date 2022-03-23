# 
#  HSDES API: https://hsdes.intel.com/rest/doc/
#
import requests
from requests_kerberos import HTTPKerberosAuth
import urllib3
import json    
import sys

 
# this is to ignore the ssl insecure warning as we are passing in 'verify=false'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_query(query_id):
    headers = {'Content-type':'application/json'}
    url = f'https://hsdes-api.intel.com/rest/query/{query_id}?max_results=0&fields=id%2Csubmitted_by%2Csubmitted_date%2C_qe_on_update%2C3rd_party_classification%2Capplication_name%2Cassigned_to%2Cawait_triage_date%2Cawaiting_customer_date%2Cawaiting_debug_date%2Cawaiting_development_date%2Cawaiting_submitter_date%2Cawaiting_triage_date%2Cccn_fix_id%2Cccn_regression_id%2Cck_tmp%2Cclassic_attachment_link%2Cclassic_id%2Cclassic_info%2Cclassic_related_link%2Cclassic_rev%2Cclassic_url%2Ccomplexity%2Ccomponent_counter%2Ccomponent_updated_date%2Ccustomer_company%2Ccustomer_detail%2Ccustomer_disclosure%2Ccustomer_owner%2Cdata_debug_feedback_loop%2Cdcn_regression_id%2Cdebug_date%2Cdebug_description%2Cdebug_gde_date%2Cdevelopment_date%2Cdo_not_autoclone_qe%2Ces_fail%2Cext_additional_info%2Cext_attach_url%2Cext_attach_url_from%2Cext_attach_url_to%2Cext_atten_required%2Cext_blocking%2Cext_commit_available_build%2Cext_current_flighting_build%2Cext_current_release_build%2Cext_cust_blog%2Cext_cust_blog_hist%2Cext_cust_blog_rev%2Cext_duplicate_id%2Cext_duplicate_id_status%2Cext_engagement%2Cext_feature%2Cext_kit_type%2Cext_os_product%2Cext_os_release%2Cext_priority%2Cext_resolution%2Cext_shared_tagging%2Cext_source_db%2Cext_source_id%2Cext_source_url%2Cext_status%2Cext_sync_to_source%2Cext_sync_to_target%2Cext_target_db%2Cext_target_id%2Cext_target_jira_id%2Cext_target_url%2Cext_update_flag%2Cexternal_approved_resolution%2Cexternal_approved_title%2Cfailing_system_location%2Cfix_build_label%2Cfix_commit_id%2Cfix_needed_by%2Cfix_needed_by_date%2Cfocus_feature%2Cform_factor%2Cfound_in_project%2Cfrom_id_post_migration%2Cfrom_tenant_platform_family%2Cfuture_date%2Cgde_comment%2Cgdhm%2Cgerrit_fix%2Cgfx_baseline%2Cgfx_branch%2Cgfx_driver_version%2Cgop_vbios_version%2Cgop_version%2Chow_found%2Chow_found_details%2Chow_found_temp%2Cimplemented_date_after1april2018%2Cin_es_sync_group%2Cinstaller_version%2Cinternal_priority%2Cinternal_summary%2Cis_bridge_group%2Cis_bug_requested_fix_admin%2Cis_bug_target_release%2Cis_component_affected_unassigned%2Cis_component_gop_driver%2Cis_component_graphics_driver%2Cis_component_graphics_test%2Cis_component_installer%2Cis_component_isv%2Cis_component_unassigned%2Cis_customer_disclosure_admin%2Cis_internal_priority_admin%2Cis_log_sufficient%2Cis_ms_bridge_acct%2Cis_platform_excluded%2Cis_regression%2Cis_state_implemented%2Cis_submitter_org_graphics%2Cisv%2Cjira_status%2Clogin_snapshot%2Cmarket_segment%2Cmsft_blocked%2Codm%2Corig_ext_src_db%2Corig_ext_src_id%2Corig_ext_src_url%2Cos_version%2Cowner_debug%2Cowner_development%2Cowner_resolved%2Cowner_triage%2Cowner_verify_failed%2Cpcgsw_platform%2Cpch%2Cphase%2Cplatform_from_tenant%2Cprioritized_date%2Cproblem_classification%2Cpromoted_date%2Cregression%2Cregression_build_label%2Cregression_commit_id%2Crejected_confirmed%2Crejected_date%2Creopen_date%2Creproducible_on_crb%2Cresolution_type%2Csub_component%2Csubmitted_ww%2Csubmitter_org%2Csuspected_security_issue%2Csync_attach_to_target%2Ctarget_release%2Ctarget_release_date%2Cteam%2Ctest_cycle%2Ctest_name%2Ctest_owner%2Ctest_tool%2Ctmp_customer_detail%2Ctriage_date%2Ctriage_quality_status%2Cupload_attach_to_msft%2Cverified_version%2Cverify_failed_date%2Cwhql_impact'
    response = requests.get(url, verify=False, auth=HTTPKerberosAuth(), headers=headers)
    results = response.json()
    json_data = results['data']
    with open(str(query_id)+'_custom.json', 'w+') as json_file:
        json_file.write(json.dumps(json_data))
    return json_data

def get_query_offline(query_id):
    with open(str(query_id)+'_custom.json', 'r') as json_file:
        json_data = json.loads(json_file.read())
    return json_data

def get_field_value_set(query_data, field_name):
    field_value_set = set()
    for data in query_data:
        if len(data[field_name]) > 0:
            field_value_set.add(data[field_name])
    return field_value_set

def get_field_value_stat(query_data, field_name):
    field_value_set = set()
    field_value_list = list()
    field_stat = {}
    for data in query_data:
        if len(data[field_name]) > 0:
            field_value_set.add(data[field_name])
            field_value_list.append(data[field_name])
    for field_value in field_value_set:
        field_stat.update({field_value:field_value_list.count(field_value)})
    field_stat.update({'unique':len(field_value_set)})
    return field_stat

query_data = []

#query_data = get_query(18010329045)
query_data = get_query_offline(18010329045)



no_values_field_counter = 0
no_values_field_list = list()

one_values_field_counter = 0
one_values_field_list = list()

for query_field in query_data[0].keys():
    field_values = get_field_value_set(query_data,query_field)
    field_values_count = len(field_values)
    if field_values_count == 0:
        #print(f'{query_field} - not used')
        no_values_field_list.append(query_field)
        no_values_field_counter += 1
    else:
        if field_values_count == 1:
            print(f'{query_field} unique values: {field_values_count}')
            print(f'values: {field_values}')
            print(get_field_value_stat(query_data,query_field))
            one_values_field_list.append(query_field)
            one_values_field_counter += 1

print(f'\n\n    nr of records: {len(query_data)}')
print(f'all custom fields: {len(query_data[0].keys())}')  
print(f'        one value: {one_values_field_counter}')       
print(f'         not used: {no_values_field_counter}\n\n') 

for field in no_values_field_list:
    print(field)

#print(get_field_value_set(query_data,'application_name'))
    




