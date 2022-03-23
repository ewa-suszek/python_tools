import requests
from requests.auth import HTTPBasicAuth
import json
'''
https://intelpedia.intel.com/Proxy_at_Intel
      
set http_proxy=http://proxy-chain.intel.com:911
set https_proxy=http://proxy-chain.intel.com:912      

to check token use: url = 'https://hsdes-api.intel.com/ws/ESService/auth' uid = '<username>' pwd = '<service token>'
https://hsdes-api.intel.com/ws/ESService/auth
'''
# https://hsdes-api.intel.com/rest/doc/#!/viewport/getAllVeiwports



#auth = ('jwojcik', 'J9E7atjmzYKLihCo3FkLoISZotj6VDOBiFG+cj+mKmKvzQlI=')

http_proxy  = "http://proxy-chain.intel.com:911"
https_proxy = "http://proxy-chain.intel.com:912"

request_header = 'Content-Type', 'application/json'

proxyDict = { 
              "http"  : http_proxy, 
              "https" : https_proxy, 
            }

#https://hsdes-api.intel.com/rest/article/1406361794
       
r = requests.get('https://hsdes-api.intel.com/ws/ESService/auth', auth=HTTPBasicAuth('jwojcik','J9E7atjmzYKLihCo3FkLoISZotj6VDOBiFG+cj+mKmKvzQlI='), proxies=proxyDict, verify=False)

print(r)
print(r.text)



