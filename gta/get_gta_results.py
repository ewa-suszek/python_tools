from connector import GtaConnector
import getpass
import pandas
import logging
import sys
import argparse

log = logging.getLogger()
log.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
log.addHandler(ch)

class GtaResults():
    def __init__(self, build_name, test_session_id, rows_per_page, rerun, user, password):
        self.gtax_address = "http://gta.intel.com"
        self.clients_api_address = "/api/results/v2"
        self.connector = GtaConnector(self.gtax_address + self.clients_api_address, user, password)
        self.build_name = build_name
        self.test_session_id = test_session_id
        self.rows_per_page = rows_per_page
        self.rerun = rerun

        self.parsed_results = []

    def get_page_gta_results(self, page):
        filter_data = \
            {"builds": [{"build": self.build_name,
                            "filters": {"test_session": self.test_session_id}}
                        ]}
                        
        print(f"/results?build_name={self.build_name}&include_count=false"
                                             f"&changes_only=false&skip_missing=false&rerun={self.rerun}"
                                             f"&page={page}&rows_per_page={self.rows_per_page}")
                                             
        print(filter_data)
        results = self.connector.post_to_url(f"/results?build_name={self.build_name}&include_count=false"
                                             f"&changes_only=false&skip_missing=false&rerun={self.rerun}"
                                             f"&page={page}&rows_per_page={self.rows_per_page}", filter_data)

        print(results)
        
        if not results["builds"][0]["items"]:
            log.error("GTA Results not found! Nothing to compare.")
            sys.exit(1)
        log.info("Found %s GTA results for page %s" % (len(results["builds"][0]["items"]), page))
        return results

    def parse_page_gta_results(self, results, page=None):
        log.debug("Parsing results for page %s" % page)
        page_results = results["builds"][0]["items"]
        temp_results = []
        for result in page_results:
            task_det = {}
            task_det["item"] = result["item_name"]
            task_det["args"] = result["args"]
            task_det["component"] = result["component"]
            task_det["platform"] = result["platform"]
            task_det["build"] = result["build_name"]
            task_det["os"] = result["os"]
            task_det["status"] = result["status"]
            task_det["tags"] = result["tags"]
            task_det["rerun_info"] = result["rerun_info"]
            task_det["url"] = result["test_run_url"]
            temp_results.append(task_det)
        log.info("%s results have been parsed for results page %s. Appending..." % (len(temp_results), page))
        self.parsed_results.extend(temp_results)

    def get_gta_results(self):
        log.info("Getting all results for session %s" % self.test_session_id)
        next_page_exists = True
        page = 1
        while next_page_exists:
            results = self.get_page_gta_results(page)
            self.parse_page_gta_results(results, page)

            next_page_exists = results["paging"]["next_page_exists"]
            page+=1

        return self.parsed_results


def get_results(args):
    gta_comparison = GtaResults(build_name=args.build_name, test_session_id=args.test_session_id,
                                rows_per_page=args.rows_per_page, rerun=args.rerun, user=getpass.getuser(),
                                password=getpass.getpass())
    gta_comparison.get_gta_results()

    log.info("Merged %s results." % len(gta_comparison.parsed_results))

    results_frame = pandas.DataFrame(gta_comparison.parsed_results)
    results_frame = results_frame[["platform", "os", "component", "item", "args", "build", "status", "tags",
                                   "rerun_info", "url"]]
    results_frame.to_excel("results.xlsx", index=False)
    log.info("Results have been saved to file results.xlsx")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description="Get GTA test session result")

    parser.add_argument("--build_name", type=str, required=True, help="gfx build name")
    parser.add_argument("--test_session_id", type=str, required=True, help="test session id")
    parser.add_argument("--rows_per_page", type=str, default=1000, required=False, help="rows per page")
    parser.add_argument("--rerun", type=str, default="all", required=False,
                        choices=["all", "best", "first", "last", "worst"], help="Rerun type")
    parser.set_defaults(func=get_results)
    args = parser.parse_args()
    print(getpass.getuser())
    args.func(args)