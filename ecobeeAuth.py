import pickle

CREDENTIAL_PICKLE = '.credential'


class EcobeeAuth:
    _authCode: str = None
    _refreshToken: str = None

    def __load__(self):
        loadedAuth = None
        try:
            with open(CREDENTIAL_PICKLE, 'rb') as file:
                loadedAuth = pickle.load(file)
            assert isinstance(loadedAuth, EcobeeAuth)
            return loadedAuth
        except FileNotFoundError or AssertionError:
            return None

    def __save__(self):
        with open(CREDENTIAL_PICKLE, 'wb') as file:
            pickle.dump(self, file)

    def __init__(self):
        loadedAuth = self.__load__()
        if loadedAuth is not None:
            self._authCode = loadedAuth._authCode
            self._refreshToken = loadedAuth._refreshToken

    @property
    def authCode(self):
        return self._authCode

    @authCode.setter
    def authCode(self, newAuthCode):
        if newAuthCode is None or len(newAuthCode) < 1:
            return
        self._authCode = newAuthCode
        self.__save__()

    @property
    def refreshToken(self):
        return self._refreshToken

    @refreshToken.setter
    def refreshToken(self, newRefreshToken):
        if newRefreshToken is None or len(newRefreshToken) < 1:
            return
        self._refreshToken = newRefreshToken
        self.__save__()
