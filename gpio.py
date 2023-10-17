from configuration import config

testMode = False

try:
    import RPi.GPIO
except ImportError:
    print("Unable to import RPi.GPIO, running in test mode")
    testMode = True


class GPIO():
    _testMode = None
    _pinNumber = None
    _pinOn = None

    def __updatePin(self):
        if self._testMode:
            print("Would set pin to {}".format("on" if self._pinOn else "off"))
            return

        RPi.GPIO.output(self._pinNumber, self._pinOn)

    def __init__(self):
        self._testMode = testMode
        self._pinNumber = int(config.get('Environment', 'PinNumber', None))
        self._pinOn = False

        if not self._testMode:
            RPi.GPIO.setmode(RPi.GPIO.BOARD)
            RPi.GPIO.setup(self._pinNumber, RPi.GPIO.OUT)

        self.__updatePin()

    def setOn(self):
        if (self._pinOn is True):
            return
        self._pinOn = True
        self.__updatePin()

    def setOff(self):
        if (self._pinOn is False):
            return
        self._pinOn = False
        self.__updatePin()

    def isOn(self):
        return self._pinOn is True

    def isOff(self):
        return self._pinOn is False
