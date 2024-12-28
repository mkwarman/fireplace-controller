from configuration import config

testMode = False

try:
    import RPi.GPIO
except ImportError:
    print("Unable to import RPi.GPIO, running in test mode")
    testMode = True


class GPIO():
    _testMode = None

    _fireplacePinNumber = None
    _indicatorPinNumber = None
    _buttonPinNumber = None

    _fireplacePinOn = None
    _indicatorPinOn = None

    def __updatePin(self, pinNumber, isOn):
        if self._testMode:
            print("Test mode: Would set pin {pinNumber} to {onOrOff}".format(pinNumber=pinNumber, onOrOff=("on" if self._fireplacePinOn else "off")))
            return

        RPi.GPIO.output(pinNumber, isOn)

    def __init__(self):
        self._testMode = testMode
        self._fireplacePinNumber = int(config.get('Environment', 'FireplacePinNumber', None))
        self._indicatorPinNumber = int(config.get('Environment', 'IndicatorPinNumber', None))
        self._buttonPinNumber = int(config.get('Environment', 'ButtonPinNumber', None))
        self._fireplacePinOn = False
        self._indicatorPinOn = False

        if not self._testMode:
            RPi.GPIO.setmode(RPi.GPIO.BOARD)

            RPi.GPIO.setup(self._fireplacePinNumber, RPi.GPIO.OUT)
            RPi.GPIO.setup(self._indicatorPinNumber, RPi.GPIO.OUT)
            RPi.GPIO.setup(self._buttonPinNumber, RPi.GPIO.IN, pull_up_down=RPi.GPIO.PUD_UP)
        else:
            print("Test mode: Would initialize pin inputs and outputs")

        self.__updatePin(self._fireplacePinNumber, self._fireplacePinOn)
        self.__updatePin(self._indicatorPinNumber, self._indicatorPinOn)

    def setButtonCallback(self, buttonCallback):
        if not self._testMode:
            RPi.GPIO.add_event_detect(self._buttonPinNumber, RPi.GPIO.RISING, callback=buttonCallback, bouncetime=200)
        else:
            print("Test mode: Would set event callback for button press")

    def setFireplaceOn(self):
        if (self._fireplacePinOn is True):
            return
        self._fireplacePinOn = True
        self.__updatePin(self._fireplacePinNumber, self._fireplacePinOn)

    def setFireplaceOff(self):
        if (self._fireplacePinOn is False):
            return
        self._fireplacePinOn = False
        self.__updatePin(self._fireplacePinNumber, self._fireplacePinOn)

    def setIndicatorOn(self):
        if (self._indicatorPinOn is True):
            return
        self._indicatorPinOn = True
        self.__updatePin(self._indicatorPinNumber, self._indicatorPinOn)

    def setIndicatorOff(self):
        if (self._indicatorPinOn is False):
            return
        self._indicatorPinOn = False
        self.__updatePin(self._indicatorPinNumber, self._indicatorPinOn)

    def isFireplaceOn(self):
        return self._fireplacePinOn is True

    def isFireplaceOff(self):
        return self._fireplacePinOn is False

    def isIndicatorOn(self):
        return self._indicatorPinOn is True

    def isIndicatorOff(self):
        return self._indicatorPinOn is False

    def cleanup(self):
        print("Cleaning up GPIO")
        if not self._testMode:
            RPi.GPIO.cleanup()

