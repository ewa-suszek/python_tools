from connector import GtaConnector
import getpass
import sys
import argparse

'''
curl -X POST --header 'Content-Type: application/json' --header 'Accept: application/json' 
-d '{"aggregation":{"rerun":"BEST"},"filterGroups":[{"filters":[{"tagsAnyOf":[],"tagsAllOf":[],"tagsExcept":["isolation","obsoleted","private","notAnIssue","iteration","knownNewOsIssue","gen12","newFeature","MonzaD3D11"],"vertical":["Render","Compute"],"cycle":["CI"],"environment":["Silicon"],"build":[{"name":"gfx-driver-ci-master-5332"}]}]}],"globalFilterId": "45","columns":["cycle","mappedComponent","tags","vertical"],"splitMultivalueColumns":["tags"]}' 
 'http://gta.intel.com/api/results/v2/aggregations?legacy=false&cached=true'
'''

class GtaResults():
    def __init__(self, build_name, rerun, user, password):
        if password is None:
            password = getpass.getpass()
        self.gtax_address = "http://gta.intel.com"
        self.clients_api_address = "/api/results/v2"
        self.connector = GtaConnector(self.gtax_address + self.clients_api_address, user, password)
        self.build_name = build_name
        self.rerun = rerun
        self.parsed_results = []

    def get_uber_results(self):
        post_data = \
                {"aggregation":{"rerun":self.rerun},
                "filterGroups":[{"filters":[{"tagsAnyOf":[],"tagsAllOf":[],"tagsExcept":["isolation","obsoleted","private","notAnIssue","iteration"],"vertical":["Render","Compute"],"cycle":["CI","CI-EXT"],"environment":["Silicon"],"build":[{"name":self.build_name}]}]}],
                "globalFilterId": "45",
                "columns":["cycle","mappedComponent","tags","vertical"],
                "splitMultivalueColumns":["tags"]}
        results = self.connector.post_to_url('/aggregations?legacy=false&cached=true', post_data)
        self.parsed_results.extend(results)
        return self.parsed_results

def get_cycle_result(passed, total, tags):
    limit = 1000
    if tags in ['W.GFT', 'GFT']:
        limit = 995
    rate = round(passed*1000/total,0)
    result = 1
    if rate >= limit:
        result = 0
    return result

def get_cycle_stat(cycle_dict):
    cycle_not_passed_names_list = ['canceledCount', 'errorCount', 'failedCount', 'pendingCount', 'skippedCount', 'unsupportedCount']
    cycle_stat_passed = cycle_dict['passedCount']
    cycle_stat_total = cycle_stat_passed
    for key in cycle_dict.keys():
        if key in cycle_not_passed_names_list:
            cycle_stat_total += cycle_dict[key]
    return {"passed":cycle_stat_passed, "total":cycle_stat_total, "result":get_cycle_result(cycle_stat_passed, cycle_stat_total, cycle_dict['tags'])}

def get_component_vertical_status(component_vertical_keys_list, uber_stat):
    component_vertical_status = 0
    for key in component_vertical_keys_list:
        if key in uber_stat.keys():
            component_vertical_status += uber_stat[key]['result']
    return component_vertical_status

def get_component_vertical_pass_rate(component_vertical_keys_list, uber_stat):
    passed = 0
    total = 0
    for key in component_vertical_keys_list:
        if key in uber_stat.keys():
            passed += uber_stat[key]['passed']
            total += uber_stat[key]['total']
    return round(passed*100/total,2)

def get_results(args):
    dx_10_plus_component_vertical_map = [['DirectX 10+|CI|Tier1|Render']]
    components_map = ['DirectX 10+', 'DirectX 12', 'DirectX 9', 'DirectML', 'Instrumentation', 'Level Zero', 'OpenCL', 'OpenGL', 'Vulkan']
    tags_map = [['Tier1'], ['cert', 'Khronos'], ['TopApps'], ['Tier1Perf'], ['W.GFT']]
    cycle_map = ['CI', 'CI-EXT']
    vertical_map = ['Render', 'Compute']
 
    tags_filter = ['top50', 'Khronos', 'Tier1', 'Tier1Perf', 'TopApps', 'top50defaultAPI', 'cert', 'W.GFT', 'GFT']
    #tags_filter = ['W.GFT', 'GFT']

    gta_comparison = GtaResults(build_name=args.build_name, rerun=args.rerun, user=args.gta_user, password=args.gta_pass)
    gta_comparison.get_uber_results()
    uber_stat = dict()
    #tags = set()
    #print(gta_comparison.parsed_results[0])
    for cycle in gta_comparison.parsed_results:
        #tags.add(cycle["tags"])
        if cycle["tags"] in tags_filter:
            uber_stat.update({cycle["mappedComponent"]+'|'+cycle["cycle"]+'|'+cycle["tags"]+'|'+cycle["vertical"]:get_cycle_stat(cycle)})

    for key in uber_stat.keys():
        print(key+' : '+str(uber_stat[key]['passed'])+'/'+str(uber_stat[key]['total'])+' = '+str(uber_stat[key]['result']))
    #print(tags)

    for component in components_map:
        for tags in tags_map:
            for tag in tags:
                for cycle in cycle_map:
                    for vertical in vertical_map:
                        stat_key = component + '|' + cycle + '|' + tag + '|' +vertical
                        if stat_key in uber_stat.keys():
                            print(component+'|'+cycle+'|'+tag+'|'+vertical)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Get GTA test session result")
    parser.add_argument('--build_name', type=str, required=True, help="gfx build name")
    parser.add_argument('--rerun', type=str, default="BEST", required=False, choices=["BEST_WORST", "ALL", "BEST","FIRST_LAST", "LAST", "WORST", "FIRST"], help="Rerun type")
    parser.add_argument("--gta_user", type=str, default=getpass.getuser(), required=False, help="gta user name")                        
    parser.add_argument("--gta_pass", type=str, required=False, help="gta password")                        
    parser.set_defaults(func=get_results)
    args = parser.parse_args()
    args.func(args)