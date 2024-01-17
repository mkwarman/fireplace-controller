import requests
import time
from typing import Callable, Dict
from ecobeeAuth import EcobeeAuth
from configuration import config

AUTHORIZE_URL = 'https://api.ecobee.com/authorize'
TOKEN_URL = 'https://api.ecobee.com/token'
THERMOSTAT_URL = 'https://api.ecobee.com/1/thermostat?format=json'

# Cache life is 3 minutes, per ecobee API limits
# https://www.ecobee.com/home/developer/api/documentation/v1/operations/get-thermostat-summary.shtml
CACHE_LIFE = 180
# TODO: This should be a config value
MONITOR_SENSOR_NAME = 'Home'


def isExpiredTokenResult(response: requests.Response):
    return (response.status_code == 500 and
            response.json()['status']['code'] == 14)


def getTemp(sensor):
    return next((x['value'] for x in sensor['capability']
                 if x['type'] == 'temperature'))


def starWatched(name):
    return "*" + name if name == MONITOR_SENSOR_NAME else name


class CacheEntry():
    time: float
    value: any

    def __init__(self, value):
        self.time = time.time()
        self.value = value

    def isCurrent(self):
        return (time.time() - self.time) < CACHE_LIFE


class Ecobee():
    auth: EcobeeAuth = None
    accessToken: str = None
    cache: Dict[str, CacheEntry] = {}
    overrideTargetTemp = None
    fanHoldActive = False

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

    def __getAuthHeaders__(self):
        if self.accessToken is None:
            raise Exception("Authorization required, go to /authorize")
        return {'Authorization': 'Bearer {}'.format(self.accessToken)}

    def __withRefresh__(self, func: Callable[..., requests.Response]):
        result = func()
        if not isExpiredTokenResult(result):
            return result
        self.__refreshAccessToken__()
        return func()

    def __request__(self,
                    func: Callable[..., requests.Response],
                    cacheKey: str):
        if cacheKey in self.cache and self.cache[cacheKey].isCurrent():
            return self.cache[cacheKey].value
        print("making request")
        response = self.__withRefresh__(func)
        self.cache[cacheKey] = CacheEntry(response)
        return response

    def __getInfoRuntime__(self):
        return self.__request__(
            lambda:
            requests.get(THERMOSTAT_URL,
                         headers=self.__getAuthHeaders__(),
                         params={
                            'body': '''
                            {"selection":{"selectionType":"registered",
                            "selectionMatch":"","includeRuntime":true}}
                            '''}
                         ),
            'INFO_runtime')

    def __getInfoSensors__(self):
        return self.__request__(
            lambda:
            requests.get(THERMOSTAT_URL,
                         headers=self.__getAuthHeaders__(),
                         params={
                            'body': '''
                            {"selection":{"selectionType":"registered",
                            "selectionMatch":"","includeSensors":true}}
                            '''}
                         ),
            'INFO_sensors')

    def __getInfoRuntimeSensors__(self):
        return self.__request__(
            lambda:
            requests.get(THERMOSTAT_URL,
                         headers=self.__getAuthHeaders__(),
                         params={
                            'body': '''
                            {"selection":{"selectionType":"registered",
                            "selectionMatch":"","includeRuntime":true,"includeSensors":true}}
                            '''}
                         ),
            'INFO_runtime_sensors')

    def __getInfoRuntimeSettingsStatus__(self):
        return self.__request__(
            lambda:
            requests.get(THERMOSTAT_URL,
                         headers=self.__getAuthHeaders__(),
                         params={
                            'body': '''
                            {"selection":{"selectionType":"registered",
                            "selectionMatch":"","includeRuntime":true,
                            "includeSettings":true,"includeEquipmentStatus":true}}
                            '''}
                         ),
            'INFO_runtime_settings_status')

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
        return self.__getInfoRuntimeSettingsStatus__().json()

    def getSensors(self):
        return self.__getInfoSensors__().json()

    def getEvents(self):
        # Not cached as events can happen anytime
        return self.__withRefresh__(
            lambda: requests.get(THERMOSTAT_URL,
                                 headers=self.__getAuthHeaders__(),
                                 params={
                                    'body': '''
                                    {"selection":{"selectionType":"registered",
                                    "selectionMatch":"","includeEvents":true}}
                                    '''}
                                 )).json()

    def getCurrentTemp(self):
        sensors = (self.__getInfoSensors__().json()
                   ['thermostatList'][0]
                   ['remoteSensors'])

        return int(next(getTemp(sensor) for sensor in sensors
                        if sensor['name'] == MONITOR_SENSOR_NAME))

    def getTempDifferential(self):
        """
        Returns the difference between current temp and desired heating temp in
        tenths of degrees. Positive numbers indicate the current temperature
        is warmer than desired, negative number indicate that the current
        temperature is lower than desired.
        """
        infoRuntime = self.__getInfoRuntime__()
        runtime = infoRuntime.json()['thermostatList'][0]['runtime']

        actualTemperature = int(runtime['actualTemperature'])
        setTemperature = (int(runtime['desiredHeat'])
                          if self.overrideTargetTemp is None
                          else self.overrideTargetTemp)

        return actualTemperature - setTemperature

    def setFanHold(self):
        if self.fanHoldActive:
            return

        headers = self.__getAuthHeaders__()
        self.__withRefresh__(
            lambda: requests.post(THERMOSTAT_URL, headers=headers, json={
                "selection": {
                    "selectionType": "registered",
                    "selectionMatch": ""
                },
                "functions": [
                    {
                        "type": "setHold",
                        "params": {
                            "holdType": "indefinite",
                            "fan": "on"
                        }
                    }
                ]
            })
        ).raise_for_status()
        self.fanHoldActive = True

    def resumeProgram(self):
        if not self.fanHoldActive:
            return

        headers = self.__getAuthHeaders__()
        self.__withRefresh__(
            lambda: requests.post(THERMOSTAT_URL, headers=headers, json={
                "selection": {
                    "selectionType": "registered",
                    "selectionMatch": ""
                },
                "functions": [
                    {
                        "type": "resumeProgram",
                        "params": {
                            "resumeAll": False
                        }
                    }
                ]
            })
        ).raise_for_status()
        self.fanHoldActive = False

    def setOverrideTargetTemp(self, target: int):
        self.overrideTargetTemp = target

    def clearOverrideTargetTemp(self):
        self.overrideTargetTemp = None

    def getDesiredHeat(self):
        return (self.__getInfoRuntime__().json()
                ['thermostatList'][0]
                ['runtime']
                ['desiredHeat'])

    def getSummaryData(self):
        infoJson = self.__getInfoRuntimeSensors__().json()

        runtimeTemp = int(infoJson
                          ['thermostatList'][0]
                          ['runtime']
                          ['actualTemperature'])

        desiredHeat = int(infoJson
                          ['thermostatList'][0]
                          ['runtime']
                          ['desiredHeat'])

        sensors = (infoJson
                   ['thermostatList'][0]
                   ['remoteSensors'])

        sensorList = map(lambda sensor: (starWatched(sensor['name']),
                                         getTemp(sensor)), sensors)

        return {
            "runtimeTemp": runtimeTemp,
            "desiredHeat": desiredHeat,
            "sensorList": sensorList
        }
