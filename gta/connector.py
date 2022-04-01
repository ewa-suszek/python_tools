import requests
import json

from requests.auth import HTTPBasicAuth

class GtaConnector():
    def __init__(self, address, user='annonymous', password=''):
        self.address = address
        self.user = user
        self.password = password
        self.auth = HTTPBasicAuth(self.user, self.password)

    def get_from_url(self, path, unpack=True):
        print(self.address + path)
        response = requests.get(self.address + path, auth=self.auth)
        return self.parse_response(response, unpack=unpack)

    def post_to_url(self, path, data=None) -> dict:
        response = requests.post(self.address + path, json=data, auth=self.auth)
        return self.parse_response(response)

    def parse_response(self, response, unpack=True):
        if response.status_code != 200:
            raise ConnectionError(response.reason + "" + response.text)
        data = response.json()
        if isinstance(data, dict) and unpack:
            parsed = data.get('data', None)
            if parsed is not None:
                return parsed
        return data