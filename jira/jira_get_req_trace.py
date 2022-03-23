# reference:
# JIRA module docs: https://jira.readthedocs.io/en/master/installation.html
# ZEPHYR https://getzephyr.docs.apiary.io/#

from jira import JIRA
import re
import os
import sys
import json
import base64
import requests
from datetime import datetime
from getpass import getpass
from requests_kerberos import HTTPKerberosAuth
import urllib3
urllib3.disable_warnings()

def main(argv):
    global my_hashed_password
    
    # -----------------------------------------------------------------------------------------
    #
    #  projects list: 
    #    project_name, jira_query, test_cycle_name
    #
    # -----------------------------------------------------------------------------------------

    project_index = 2

    projects_list = []
    projects_list.append(['DMP_WW49','project = "data management platform solution" AND type = Requirement AND fixVersion in ("ww39.5 Q3\'19 Release", "End Q4\'19 Release" ) AND resolution not in ("3rd Party", Duplicate) AND labels != link_to_doc and component != PFrame','2019/11/25, 11:58  '])
    projects_list.append(['PFRAME','project = 38300 AND fixVersion = 108123 ORDER BY priority DESC, key ASC','PFT'])
    projects_list.append(['DMP_WW50','project = "data management platform solution" AND type = Requirement AND fixVersion in ("ww39.5 Q3\'19 Release", "End Q4\'19 Release" ) AND resolution not in ("3rd Party", Duplicate) AND labels != link_to_doc and component != PFrame','2019/12/10, 10:41'])
    
    project_name = projects_list[project_index][0]
    jira_query = projects_list[project_index][1]
    test_cycle_name = projects_list[project_index][2]

    
    # -----------------------------------------------------------------------------------------
    
    script_mode = 'online'
    #script_mode = 'offline'

    req_trace_list = list()
    result_dic = {}
    test_results_stat_list = []
    cov_dict = {} # {REQ_ID:{'COV_PASS':1, 'COV_TOTAL':3, 'TESTS':{'TEST_ID1':'PASS','TEST_ID2':'FAIL','TEST_ID3':'FAIL'} } }
    components_cov_dict = {} 


    if len(sys.argv) > 1:
        if sys.argv[1] == '--offline':
            script_mode = 'offline'
    
    if script_mode == 'offline':
        req_trace_list, result_dic = get_req_and_tests_offline(project_name)
    else:
        my_hashed_password = read_password()
        req_trace_list, result_dic = get_req_and_tests(project_name,jira_query,test_cycle_name)

    for req in req_trace_list:
        tests_dict = {}
        req_results_list_stat = []
        for test in req[1]:
            tests_dict.update({test:result_dic[test]})
            test_results_stat_list.append(result_dic[test])
            req_results_list_stat.append(result_dic[test])
        cov_dict.update({req[0]:{'COV_PASS':req_results_list_stat.count('PASS'), 'COV_FAIL':req_results_list_stat.count('FAIL'), 'COV_BLOCKED':req_results_list_stat.count('BLOCKED'), 'COV_UNEXECUTED':req_results_list_stat.count('UNEXECUTED'), 'COV_WIP':req_results_list_stat.count('WIP'), 'COV_NONE':req_results_list_stat.count('NONE'), 'COV_TOTAL':len(req[1]), 'TESTS':tests_dict, 'SUMMARY':req[2], 'COMPONENTS':req[3]}})

    components_cov_dict = get_components_cov(cov_dict)

    print(tests_summary_text(test_cycle_name,test_results_stat_list))
    print(cov_summary_text(cov_dict))
    print(cov_components_summary_text(components_cov_dict))
    
    with open(project_name.lower()+'_cov_status.txt', 'w+') as cov_file:
        cov_file.write(tests_summary_text(test_cycle_name,test_results_stat_list))
        cov_file.write(cov_summary_text(cov_dict))
        cov_file.write(cov_components_summary_text(components_cov_dict))
        cov_file.write(cov_text_format(cov_dict,'all:'))
        cov_file.write(cov_covered_not_covered_list(cov_dict))
    
    ts = get_timestamp()
    ts = 'latest'
    html_file_name = ts+'-'+project_name.lower()+'_cov_status.html'

    with open(html_file_name,'w+') as cov_html_file:
        cov_html_file.write(cov_html_format(cov_dict,components_cov_dict,test_cycle_name,test_results_stat_list,project_name))

    print(f'coverage status saved in {project_name.lower()}_cov_status.txt and {html_file_name}')
    #print(cov_dict)

# end main()

def read_password():
    try:
        pass_file = open(os.path.join(os.environ['USERPROFILE'], '.python_jira'), "rb+")
        hashed_pass = pass_file.read()
    except:
        password = getpass()
        hashed_pass = base64.b64encode(str.encode(password))
        pass_file = open(os.path.join(os.environ['USERPROFILE'], '.python_jira'), "ab+")
        pass_file.write(hashed_pass)
    pass_file.close()
    return hashed_pass

def get_user_name_and_pass(your_hashed_pass):
    return os.environ['USERNAME'], base64.b64decode(your_hashed_pass).decode('utf-8')


def get_req_and_tests(project_name,query,cycle_name):
    jira = JIRA(options={'server': 'https://jira.devtools.intel.com','verify':False}, basic_auth=(get_user_name_and_pass(my_hashed_password)[0], get_user_name_and_pass(my_hashed_password)[1]), proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    req_list = jira.search_issues(query, maxResults=1500, fields='id,key,issuelinks,summary,components')

    trace_list = list()
    tests_set = set()
    tests_results_dict = {}
    

    # [[req1_key,[test11_key,test12_key],title1,[component1]],[req2_key,[test21_key,test22_key],title2,[component1,component2]]]

    for req in req_list:
        tests_list = list()
        req_components_list = list()
        for link in req.fields.issuelinks:
            try: 
                link_type = link.outwardIssue.fields.issuetype.id
                if link_type == '11600':
                # 11600 -> test type id
                    tests_set.add(link.outwardIssue.key)
                    tests_list.append(link.outwardIssue.key)
            except :
                pass
            try:
                link_type = link.inwardIssue.fields.issuetype.id
                if link_type == '11600':
                # 11600 -> test type id
                    tests_set.add(link.inwardIssue.key)
                    tests_list.append(link.inwardIssue.key)
            except :
                pass
        
        for component in req.fields.components:
            req_components_list.append(component.name)

        trace_list.append((req.key,tests_list,req.fields.summary,req_components_list))

    with open(project_name.lower()+'_trace_tmp.json', 'w+') as trace_file:
        trace_file.write(json.dumps(trace_list))

    for test in tests_set:
        print(str(len(tests_results_dict)+1)+'/'+str(len(tests_set))+' - getting result for '+test)
        tests_results_dict[test]=get_cycle_result_for_test_case(test,cycle_name)

    with open(project_name.lower()+'_results_dic_tmp.json', 'w+') as results_file:
        results_file.write(json.dumps(tests_results_dict))

    return trace_list,tests_results_dict

def get_req_and_tests_offline(project_name):
    trace_list = list()
    tests_results_dict = {}

    with open(project_name.lower()+'_trace_tmp.json', 'r') as trace_file:
        trace_list = json.loads(trace_file.read())

    with open(project_name.lower()+'_results_dic_tmp.json', 'r') as results_file:
        tests_results_dict = json.loads(results_file.read())

    return trace_list,tests_results_dict


def get_cycle_result_for_test_case(test_case_key,cycle_name):
    result = 'NONE'
    headers = { 'Content-type': 'application/json' }
    url = 'https://jira.devtools.intel.com/rest/zapi/latest/traceability/executionsByTest?testIdOrKey='+test_case_key+'&maxRecords=&offset='
    response = requests.get(url, verify=False, auth=requests.auth.HTTPBasicAuth(get_user_name_and_pass(my_hashed_password)[0],get_user_name_and_pass(my_hashed_password)[1]), headers = headers,  proxies={'http': 'http://proxy-chain.intel.com:911', 'https': 'http://proxy-chain.intel.com:912' })
    try:
        executions = response.json()
        for exe in range(int(executions['totalCount'])):
            if cycle_name == executions['executions'][exe]['execution']['testCycle']:
                result = executions['executions'][exe]['execution']['status']
    except:
        pass
    return result

def cov_text_format(cov_dict, title):
    cov_text = '\n--------------------------------------------------------------------------------------------------------\n'
    cov_text += title
    cov_text += '\n--------------------------------------------------------------------------------------------------------\n'
    for req in cov_dict:
        cov_text += req+' ['+str(cov_dict[req]['COV_PASS'])+'/'+str(cov_dict[req]['COV_TOTAL'])+']\n'
        for test in cov_dict[req]['TESTS']:
            cov_text += '  '+test+':'+cov_dict[req]['TESTS'][test]+'\n'
        cov_text += '\n'
    cov_text += '\n--------------------------------------------------------------------------------------------------------\n'
    return cov_text

def cov_html_format(cov_dict,components_cov_dict,title,test_results_stat_list,project_name):
    ts = get_timestamp()
    bars_width = '900'
    html_text = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>'+ts+' '+project_name+' COVARAGE REPORT</title>\n'
    html_text += '<style>\n'
    html_text += 'body{font-weight: normal;font-family:Verdana, Geneva, Tahoma, sans-serif; text-align: left; font-size: 12px;}\n'
    html_text += '.stacked-bar-graph {width: 100%;height: 22px;padding:0; margin-top: 2px; margin-bottom: 0px;}\n'
    html_text += '.stacked-bar-graph span {height: 20px;float: left;padding:0;border-radius: 3px;text-align: center; }\n'
    html_text += '.stacked-bar-graph-total {width: 100%;height: 62px;padding:0; margin-top: 2px; margin-bottom: 0px;}\n'
    html_text += '.stacked-bar-graph-total span {height: 60px;float: left;padding:0;border-radius: 3px;text-align: center; font-size: 20px;}\n'
    html_text += '.stacked-bar-graph .pass, .stacked-bar-graph-total .pass {background:green;color: white;}\n'
    html_text += '.stacked-bar-graph .fail, .stacked-bar-graph-total .fail {background: red;color: white;}\n'
    html_text += '.stacked-bar-graph .blocked, .stacked-bar-graph-total .blocked {background: grey;color: white;}\n'
    html_text += '.stacked-bar-graph .none, .stacked-bar-graph-total .none {background: darkred;color: white;}\n'
    html_text += '.stacked-bar-graph-total .not_cov {background: black;color: white;}\n'
    html_text += '.stacked-bar-graph .unexecuted, .stacked-bar-graph-total .unexecuted {background: darkgray;color: white;}\n'
    html_text += '.stacked-bar-graph .wip, .stacked-bar-graph-total .wip {background: lime ;}\n'
    html_text += '.btn {background-color: white; color: black; padding: 1px; font-size: 12px; border: none; cursor: pointer;}'
    html_text += '.btn:hover, .btn:focus { background-color:white;}'
    html_text += '.tests_details {display: none;}'
    html_text += '.show {display: block;}'
    html_text += 'table {border-collapse: collapse;border-spacing: 0;}\n'
    html_text += 'td{vertical-align: top;}\n'
    html_text += '</style>\n'
    html_text += '</head><body><center><h3>'+ts+' '+project_name+' COVARAGE REPORT</h3>'
    html_text += '<h3>TOTAL COMPONENTS COVARAGE STATUS</h3>'
    html_text += '<div style="width:'+bars_width+'px">\n'
    html_text += html_bar_graph_total_cov(components_cov_dict)
    html_text += '</div>\n\n'
    html_text += '<h3>COMPONENTS COVARAGE STATUS DETAILED</h3>\n'
    html_text += html_bar_graph_detailed_components_cov(components_cov_dict,bars_width)
    html_text += '<h3>TOTAL REQUIREMENTS COVARAGE STATUS</h3>'
    html_text += '<div style="width:'+bars_width+'px">\n'
    html_text += html_bar_graph_total_cov(cov_dict)
    html_text += '</div>\n\n'
    html_text += '<h3>REQUIREMENTS COVARAGE STATUS DETAILED</h3>\n'
    html_text += html_bar_graph_detailed_cov(cov_dict,bars_width,'req')
    html_text += text_2_html(tests_summary_text(title,test_results_stat_list))
    html_text += text_2_html(cov_summary_text(cov_dict))
    html_text += '</center>'
    html_text += '<script>function showTests(id_tests,id_button) {document.getElementById(id_tests).classList.toggle(\'show\');if(document.getElementById(id_tests).classList.contains(\'show\')){document.getElementById(id_button).innerHTML  = \'[-]\';}else{document.getElementById(id_button).innerHTML  = \'[+]\';}}</script>'
    html_text += '</body>\n</html>\n'
    return html_text


def html_bar_graph_detailed_cov(cov_dict,width,div_prefix):
    html_bar_graph = '<table width="'+width+'px" border="0px" cellpadding="0px">'
    req_sort_list = []

    for req in cov_dict:
        req_sort_list.append([round(cov_dict[req]['COV_PASS']/cov_dict[req]['COV_TOTAL']*100,4),cov_dict[req]['COV_PASS'],cov_dict[req]['COV_WIP'],cov_dict[req]['COV_BLOCKED'],cov_dict[req]['COV_UNEXECUTED'],cov_dict[req]['COV_TOTAL'],req])

    req_sort_list.sort(reverse=True)

    for sort_req in req_sort_list:
        req = sort_req[6]
        html_bar_graph += '<tr><td width="160px" title="'+cov_dict[req]['SUMMARY']+' ['+",".join(cov_dict[req]['COMPONENTS'])+']"><div style="margin-top: 4px; margin-right: 4px; text-align: right;">'
        html_bar_graph += html_req_link(req,cov_dict[req]['COV_PASS'],cov_dict[req]['COV_TOTAL'])
        html_bar_graph += ' ' + html_menu_button(div_prefix+req)
        html_bar_graph += '</div></td><td><div class="stacked-bar-graph">\n'
        for status in ['COV_PASS','COV_FAIL','COV_WIP','COV_BLOCKED','COV_UNEXECUTED','COV_NONE']:
            if cov_dict[req][status] > 0:
                html_bar_graph += html_bar_req(round(cov_dict[req][status]/cov_dict[req]['COV_TOTAL']*100,3),status[4:],status[4:].lower())
        html_bar_graph += '</div><div id="'+div_prefix+req+'_tests" class="tests_details"><table width="100%" border="0px" cellpadding="0px">'
        for test in cov_dict[req]['TESTS']:
            html_bar_graph += html_test_status_row(test,cov_dict[req]['TESTS'][test])
        html_bar_graph += '</table></div></td></tr>\n'
    html_bar_graph += '</table>'
    return html_bar_graph

def html_bar_graph_detailed_components_cov(components_cov_dict,width):
    html_bar_graph = ''
    component_sort_list = []

    for component in components_cov_dict:
        component_sort_list.append([round(components_cov_dict[component]['COV_PASS']/components_cov_dict[component]['COV_TOTAL']*100,4),components_cov_dict[component]['COV_PASS'],components_cov_dict[component]['COV_TOTAL'],components_cov_dict[component]['COV_NONE'],component])

    component_sort_list.sort(reverse=True)

    for component in component_sort_list:
        html_bar_graph += '<table width="'+width+'px" border="0px" cellpadding="0px">'
        html_bar_graph += '<tr><td width="350px"><div style="margin-top: 4px; margin-right: 4px; text-align: right;">'
        html_bar_graph += '<strong>'+component[4]+ ' ['+ str(component[1]) + '/'+ str(component[2]) + ']</strong>'
        html_bar_graph += ' ' + html_menu_button(component[4].replace(' ','').lower())
        html_bar_graph += '</div></td><td><div class="stacked-bar-graph">\n'
        if component[2] > 0:
            if component[1] > 0:
                    html_bar_graph += html_bar_req(round(component[1]/component[2]*100,3),'PASS','pass')
            if (component[2] - component[1] - component[3])> 0:
                    html_bar_graph += html_bar_req(round((component[2] - component[1] - component[3])/component[2]*100,3),'FAIL','fail')
            if component[3] > 0:
                    html_bar_graph += html_bar_req(round(component[3]/component[2]*100,3),'NONE','none')
        html_bar_graph += '</div><div id="'+component[4].replace(' ','').lower()+'_tests" class="tests_details"><table width="550px" border="0px" cellpadding="0px">'
        html_bar_graph += html_bar_graph_detailed_cov(components_cov_dict[component[4]]['REQ'],'550px',component[4].replace(' ','').lower())
        html_bar_graph += '</table></div></td></tr>\n'
        html_bar_graph += '</table>'
    return html_bar_graph

def html_req_link(req_id,counter,total):
    return '<a href="https://jira.devtools.intel.com/browse/'+req_id+'" target="new"><strong>'+req_id+' ['+str(counter)+'/'+str(total)+']</strong></a>'

def html_test_link(test_id):
    return '<a href="https://jira.devtools.intel.com/browse/'+test_id+'" target="new"><strong>'+test_id+'</strong></a>'

def html_menu_button(req):
    return '<button id="'+req+'_button" onclick="showTests(\''+req+'_tests\',\''+req+'_button\')" class="btn">[+]</button>'

def html_bar_graph_total_cov_count(cov_dict):
    cov_calculation_list = calc_cov_total(cov_dict)
    total_pass = cov_calculation_list[0]
    not_covered_counter = cov_calculation_list[1]
    total_not_tested = cov_calculation_list[2]
    total = cov_calculation_list[3]
    html_bar_graph = '<div class="stacked-bar-graph-total">'
    if total_pass > 0:
        html_bar_graph += html_bar_total_text(str(round(total_pass/total*100,2)),'TOTAL COVERED','pass',total_pass)
    if total_pass > 0:
        html_bar_graph += html_bar_total_text(str(round((total-total_pass-total_not_tested-not_covered_counter)/total*100,2)),'TOTAL FILED','fail',(total-total_pass-total_not_tested-not_covered_counter))
    if total_not_tested > 0:
        html_bar_graph += html_bar_total_text(str(round(total_not_tested/total*100,2)),'TOTAL NOT TESTED','none',total_not_tested)
    if not_covered_counter > 0:
        html_bar_graph += html_bar_total_text(str(round(not_covered_counter/total*100,2)),'TOTAL NOT COVERED','not_cov',not_covered_counter)
    html_bar_graph += '</div>\n'
    return html_bar_graph

def html_bar_graph_total_cov(cov_dict):
    cov_calculation_list = calc_cov_total(cov_dict)
    total_pass = cov_calculation_list[0]
    not_covered_counter = cov_calculation_list[1]
    total_not_tested = cov_calculation_list[2]
    total = cov_calculation_list[3]
    html_bar_graph = '<div class="stacked-bar-graph-total">'
    if total_pass > 0:
        html_bar_graph += html_bar_total(str(round(total_pass/total*100,2)),'TOTAL COVERED','pass')
    if total_pass > 0:
        html_bar_graph += html_bar_total(str(round((total-total_pass-total_not_tested-not_covered_counter)/total*100,2)),'TOTAL FILED','fail')
    if total_not_tested > 0:
        html_bar_graph += html_bar_total(str(round(total_not_tested/total*100,2)),'TOTAL NOT TESTED','none')
    if not_covered_counter > 0:
        html_bar_graph += html_bar_total(str(round(not_covered_counter/total*100,2)),'TOTAL NOT COVERED','not_cov')
    html_bar_graph += '</div>\n'
    return html_bar_graph
    
 
def html_bar_req(width,title,style):
    return '<span style="width:'+str(width)+'%" class="'+style+'" title="'+title+':'+str(width)+'"><div style="margin-top: 2px;">'+str(width)+'%</div></span>\n'

def html_bar_total(width,title,style):
    return '<span style="width:'+str(width)+'%" class="'+style+'" title="'+title+':'+str(width)+'"><div style="margin-top: 18px;">'+str(width)+'%</div></span>\n'

def html_bar_total_text(width,title,style,text):
    return '<span style="width:'+str(width)+'%" class="'+style+'" title="'+title+':'+str(width)+'"><div style="margin-top: 18px;">'+str(text)+'</div></span>\n'

def html_bar_test(status):
    return '<span style="width:100%" class="'+status.lower()+'" title="'+status+'"><div style="margin-top: 2px;">'+status+'</div></span>\n'

def html_test_status_row(test_id,status_test):
    html_test_status_row = '<tr><td width="80px"><div style="margin-top: 4px;">'
    html_test_status_row += html_test_link(test_id)
    html_test_status_row += '</div></td><td><div class="stacked-bar-graph">'
    html_test_status_row += html_bar_test(status_test)
    html_test_status_row += '</div></td></tr>'
    return html_test_status_row


def tests_summary_text(test_cycle_name,test_results_stat_list):
    tests_summary = '\n\n=====================================================\n'
    tests_summary += 'test cycle: '+test_cycle_name+'\n'
    tests_summary += '=====================================================\n'
    for test_status in set(test_results_stat_list):
        if test_status == 'NONE':
            tests_summary += f'{test_status}:{test_results_stat_list.count(test_status)} (---%) ({round(test_results_stat_list.count(test_status)/len(test_results_stat_list)*100,2)}% PV)\n'
        else:
            tests_summary += f'{test_status}:{test_results_stat_list.count(test_status)} ({round(test_results_stat_list.count(test_status)/(len(test_results_stat_list)-test_results_stat_list.count("NONE"))*100,2)}%) ({round(test_results_stat_list.count(test_status)/len(test_results_stat_list)*100,2)}% PV)\n'
    tests_summary += '=====================================================\n'
    tests_summary += 'TOTAL PASS:'+str(test_results_stat_list.count('PASS'))+'/'+str(len(test_results_stat_list))+'\n'
    tests_summary += 'TOTAL PASS RATE:'+str(round(test_results_stat_list.count('PASS')/len(test_results_stat_list)*100,2))+'%\n' 
    tests_summary += 'TOTAL TEST RESULTS:'+str(len(test_results_stat_list)-test_results_stat_list.count('NONE'))+'/'+str(len(test_results_stat_list))+'\n'
    tests_summary += 'TOTAL PV SCOPE:'+str(round((len(test_results_stat_list)-test_results_stat_list.count('NONE'))/len(test_results_stat_list)*100,2))+'%\n' 
    tests_summary += '=====================================================\n'
    return tests_summary

def calc_cov_total(cov_dict):
    total_stat = []
    for req in cov_dict:
        if cov_dict[req]['COV_PASS'] == cov_dict[req]['COV_TOTAL']:
            total_stat.append('COV')
        if cov_dict[req]['COV_TOTAL'] == 0:
            total_stat.append('N_C')
        if cov_dict[req]['COV_NONE'] == cov_dict[req]['COV_TOTAL']:
            total_stat.append('N_T')
    return [total_stat.count('COV'),total_stat.count('N_C'),total_stat.count('N_T'),len(cov_dict)]

def cov_summary_text(cov_dict):
    cov_calculation_list = calc_cov_total(cov_dict)
    covered_counter = cov_calculation_list[0]
    not_covered_counter = cov_calculation_list[1]
    not_tested_counter = cov_calculation_list[2]
    total = cov_calculation_list[3]
    cov_summary = '\n=====================================================\n'
    cov_summary += 'total verify:'+str(covered_counter)+'/'+str(total)+' ['
    cov_summary += str(round(covered_counter/total*100,2))+'%]\n'
    cov_summary += 'total not covered: '+str(not_covered_counter)+'/'+str(total)+' ['        
    cov_summary += str(round(not_covered_counter/total*100,2))+'%]\n'
    cov_summary += 'total not tested: '+str(not_tested_counter)+'/'+str(total)+' ['        
    cov_summary += str(round(not_tested_counter/total*100,2))+'%]\n'
    cov_summary += '=====================================================\n'
    return cov_summary


def text_2_html(text):
    text_2_html = '<pre style="font-size: 14px; font-weight: bold;">'
    text_2_html += text
    text_2_html += '</pre>\n'
    return text_2_html

def cov_covered_not_covered_list(cov_dict):
    cov_list_text = ''
    covered_dict = {}
    not_covered_dict = {}
    not_tested_dict = {}

    for req in cov_dict:
        if cov_dict[req]['COV_PASS'] == cov_dict[req]['COV_TOTAL']:
            covered_dict.update({req:cov_dict[req]})
        if cov_dict[req]['COV_TOTAL'] == 0:
            not_covered_dict.update({req:cov_dict[req]})
        if cov_dict[req]['COV_NONE'] == cov_dict[req]['COV_TOTAL']:
            not_tested_dict.update({req:cov_dict[req]})
    
    if len(covered_dict) > 0:
        cov_list_text += cov_text_format(covered_dict,'full covered list:')
    if len(not_covered_dict) > 0:
        cov_list_text += cov_text_format(not_covered_dict,'not covered list:')
    if len(not_tested_dict) > 0:
        cov_list_text += cov_text_format(not_tested_dict,'not tested list:')
    return cov_list_text

def get_timestamp():
    ts = str(datetime.now())
    ts = ts.replace(':', '_')
    return ts[:10]

def cov_components_summary_text(components_cov_dict):
    cov_components_summary_text = '\n=====================================================\n'
    for component in components_cov_dict:
        cov_components_summary_text += f"{component} - "
        for status in ['COV_PASS','COV_FAIL','COV_WIP','COV_BLOCKED','COV_UNEXECUTED','COV_NONE']:
            cov_components_summary_text += f"{status[4:]}:{components_cov_dict[component][status]} "
        cov_components_summary_text += f"TOTAL:{components_cov_dict[component]['COV_TOTAL']}\n"
    cov_components_summary_text += '=====================================================\n'
    return cov_components_summary_text

def get_components_cov(cov_dict):
    components_set = set()
    components_cov_dict = {}

    for req in cov_dict:
        for component in cov_dict[req]['COMPONENTS']:
            components_set.add(component)

    for component in components_set:
        components_req_dict = {}
        components_cov_stat = [0,0,0,0,0,0,0]
        for req in cov_dict:
            if component in cov_dict[req]['COMPONENTS']:
                components_req_dict.update({req:cov_dict[req]})
                components_cov_stat[0] += cov_dict[req]['COV_PASS']
                components_cov_stat[1] += cov_dict[req]['COV_FAIL']
                components_cov_stat[2] += cov_dict[req]['COV_BLOCKED']
                components_cov_stat[3] += cov_dict[req]['COV_UNEXECUTED']
                components_cov_stat[4] += cov_dict[req]['COV_WIP']
                components_cov_stat[5] += cov_dict[req]['COV_NONE']
                components_cov_stat[6] += cov_dict[req]['COV_TOTAL']
        components_cov_dict.update({component:{'REQ':components_req_dict, 'COV_PASS':components_cov_stat[0], 'COV_FAIL':components_cov_stat[1], 'COV_BLOCKED':components_cov_stat[2], 'COV_UNEXECUTED':components_cov_stat[3], 'COV_WIP':components_cov_stat[4], 'COV_NONE':components_cov_stat[5], 'COV_TOTAL':components_cov_stat[6],}})

    return components_cov_dict

if __name__ == '__main__':
    main(sys.argv[1:])






#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# query api call:
# https://jira.devtools.intel.com/rest/api/2/search?jql=project%20%3D%20%22data%20management%20platform%20solution%22%20AND%20type%20%3D%20Requirement%20AND%20fixVersion%20in%20(%22ww39.5%20Q3%2719%20Release%22)%20AND%20resolution%20not%20in%20(%223rd%20Party%22%2C%20Duplicate)%20AND%20labels%20!%3D%20link_to_doc%20and%20component%20!%3D%20PFrame&fields=id,key,summary,components,issuelinks
#
# result per test cycle call:
# https://jira.devtools.intel.com/rest/zapi/latest/traceability/executionsByTest?testIdOrKey=RS6-2622&maxRecords=&offset=
#
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# 
# list of test cycles:
#
# https://jira.devtools.intel.com/rest/zapi/latest/cycle?projectId=38300&versionId=&id=&offset=&issueId=&expand=
#
# test cycle results:
# https://jira.devtools.intel.com/rest/zapi/latest/execution/executionsStatusCountByCycle?projectId=38300&versionId=&cycles=62068&folders=&offset=&limit=
# 
# 
# https://jira.devtools.intel.com/secure/enav/#?query=project%20%3D%20%22RS6%22%20AND%20fixVersion%20%3D%20%22DaaS%22%20AND%20cycleName%20in%20(%222019%2F09%2F24%2C%2011%3A37%20%20%22)
#
# get execution by test
#  https://jira.devtools.intel.com/rest/zapi/latest/traceability/executionsByTest?testIdOrKey=RS6-2372&maxRecords=&offset=