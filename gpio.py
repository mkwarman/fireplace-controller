from configuration import config

try:
    import RPi.GPIO
except ImportError:
    print("Unable to import RPi.GPIO, running in test mode")
    testMode = True


class GPIO():
    pinNumber = None
    pinOn = None

    def __updatePin(self):
        if self.test:
            print("Would set pin to {}".format("on" if self.pinOn else "off"))
            return

        RPi.GPIO.output(self.pinNumber, self.pinOn)

    def __init__(self):
        self.pin = config.get('Environment', 'PinNumber', None)
        self.test = testMode

        if not self.test:
            RPi.GPIO.setmode(RPi.GPIO.BOARD)
            RPi.GPIO.setup(self.pin, RPi.GPIO.OUT)

        self.__updatePin()

    def setOn(self):
        if (self.pinOn is True):
            return       
        self.pinOn = True
        self.__updatePin()

    def setOff(self):
        if (self.pinOn is False):
            return
        self.pinOn = False
        self.__updatePin()
