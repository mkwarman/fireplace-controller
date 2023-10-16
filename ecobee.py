import requests
from ecobeeAuth import EcobeeAuth
from configuration import config

AUTHORIZE_URL = 'https://api.ecobee.com/authorize'
TOKEN_URL = 'https://api.ecobee.com/token'
INFO_URL = '''
https://api.ecobee.com/1/thermostat?format=json&body={"selection":{"selectionType":"registered","selectionMatch":"","includeRuntime":true,"includeSettings":true,"includeEquipmentStatus":true}}
'''


def isExpiredTokenError(response):
    return response.json()['status']['code'] == 14


class Ecobee():
    auth: EcobeeAuth = None
    accessToken: str = None

    def __requestAccessToken__(self):
        clientId = config.get('Auth', 'ClientId', None)
        requestResponse = requests.post(TOKEN_URL, params={
            'grant_type': 'ecobeePin',
            'code': self.auth.authCode,
            'client_id': clientId
        })
        if requestResponse.status_code != 200:
            print("Unable to request access token. Try reauthorizing at",
                  "/authorize")
            print(requestResponse.json())
            return
        jsonResponse = requestResponse.json()
        self.accessToken = jsonResponse['access_token']
        self.auth.refreshToken = jsonResponse['refresh_token']

    # This can probably be consolidated with request above
    def __refreshAccessToken__(self):
        clientId = config.get('Auth', 'ClientId', None)
        refreshResponse = requests.post(TOKEN_URL, params={
              'grant_type': 'refresh_token',
              'refresh_token': self.auth.refreshToken,
              'client_id': clientId
        })
        jsonResponse = refreshResponse.json()
        self.accessToken = jsonResponse['access_token']
        self.auth.refreshToken = jsonResponse['refresh_token']

    def __getAuthHeaders(self):
        if self.accessToken is None:
            return None
        return {'Authorization': 'Bearer {}'.format(self.accessToken)}

    def __init__(self):
        clientId = config.get('Auth', 'ClientId', None)
        if clientId is None:
            raise Exception("Missing Ecobee ClientId")

        self.auth = EcobeeAuth()

        # No auth info exists
        if self.auth.authCode is None:
            print("No Ecobee AuthCode found. Request one at /authorize to",
                  "continue")
            return

        if self.auth.refreshToken is None:
            # Have authCode but no refreshToken, so need to request
            self.__requestAccessToken__()
        else:
            # Found authCode and refreshToken, so just need to refresh
            self.__refreshAccessToken__()

    def authorize(self):
        clientId = config.get('Auth', 'ClientId', None)
        authorizeResponse = requests.get(AUTHORIZE_URL, params={
            'response_type': 'ecobeePin',
            'client_id': clientId,
            'scope': 'smartWrite'
        })
        if authorizeResponse.status_code != 200:
            print("Failed to request authorization:")
            print(authorizeResponse)
        jsonResponse = authorizeResponse.json()
        self.auth.authCode = jsonResponse['code']
        return jsonResponse['ecobeePin']

    def completeAuthorization(self):
        self.__requestAccessToken__()
        return True if self.accessToken is not None else False

    def getInfo(self):
        headers = self.__getAuthHeaders()
        if headers is None:
            return "Authorization required, go to /authorize"
        infoResponse = requests.get(INFO_URL, headers=headers)

        # Retry once after refreshing token if needed
        if (infoResponse.status_code != 200
           and isExpiredTokenError(infoResponse)):
            self.__refreshAccessToken__()
            infoResponse = requests.get(INFO_URL, headers=headers)

        return infoResponse.json()
