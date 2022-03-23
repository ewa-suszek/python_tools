'''
1306400485

https://hsdes.intel.com/rest/doc/#!/query/executeByEQL

{
  "eql": "select id,tenant,subject where Parent(id=1306400485), link_parent-child(id>0) "
}

{
  "eql": "select id,tenant,subject where parent_id=1306400485 AND subject='itp_test_case'"
}

curl -X POST --header 'Content-Type: application/json' --header 'Accept: application/json' -d '{
  "eql": "select id,tenant,subject where parent_id=1306400485 AND subject=\u0027itp_test_case\u0027"
}' 'https://hsdes-api.intel.com/rest/query/execution/eql?start_at=1'


AND subject=\''+child_subject+'\

'''
import openpyxl
from openpyxl.utils import get_column_letter
from datetime import datetime
import requests
from requests_kerberos import HTTPKerberosAuth
import urllib3
import json
import math

# this is to ignore the ssl insecure warning as we are passing in 'verify=false'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    print(get_child_ids_by_parent_id_and_child_subject('1306400485','itp_test_case'))


def get_child_ids_by_parent_id_and_child_subject(parent_id,child_subject):
    headers = { 'Content-type': 'application/json' }
    eql_query = '{"eql": "select id,tenant,subject where parent_id='+str(parent_id)+' AND subject=\''+child_subject+'\'"}'
    url = 'https://hsdes-api.intel.com/rest/query/execution/eql?start_at=1'
    response = requests.post(url, data = eql_query, verify=False, auth=HTTPKerberosAuth(), headers = headers)
    results = response.json()
    child_ids = list()
    for child in results['data']:
        child_ids.append(child['id'])
    return child_ids  


if __name__ == '__main__':
    main()