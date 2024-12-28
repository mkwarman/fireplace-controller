import sys
import time
import threading
import signal
from gpio import GPIO
from ecobee import Ecobee
from configuration import config
from flask import Flask, render_template, request, flash

if 'Environment' not in config.sections():
    raise Exception("Cannot find config data. Did you setup config.ini?")

TEMP_CHECK_DELAY_SEC = 180

app = Flask(__name__)
app.config['SECRET_KEY'] = config.get('Environment', 'SecretKey', None)
task_thread = None
gpio = GPIO()
ecobee = Ecobee()

# Global flags to control the scheduled task
eventLoopActive = False
forceRefresh = False


def checkTemps():
    tempDiff = ecobee.getTempDifferential()

    print("tempDiff: {}".format(tempDiff))
    print("fireplace.isOn(): {}".format(gpio.isFireplaceOn()))
    print("fireplace.isOff(): {}".format(gpio.isFireplaceOff()))
    print("tempDiff > 5: {}".format(tempDiff > 5))
    print("tempDiff < -5: {}".format(tempDiff < -5))
    # Current temperature is a degree greater than desired
    if gpio.isFireplaceOn() and (tempDiff > 5):
        print("should turn off")
        gpio.setFireplaceOff()
        ecobee.resumeProgram()

    # Current temperature is a degree less than desired
    if gpio.isFireplaceOff() and (tempDiff < -5):
        print("should turn on")
        gpio.setFireplaceOn()
        ecobee.setFanHold()


def eventLoop():
    global forceRefresh
    seconds = 0
    while eventLoopActive:
        if (forceRefresh or seconds % TEMP_CHECK_DELAY_SEC == 0):
            checkTemps()
            seconds = 0
            forceRefresh = False
        seconds += 1
        time.sleep(1)
    print("Thread ended")


def startThread():
    global eventLoopActive, task_thread
    if not eventLoopActive:
        eventLoopActive = True
    if not gpio.isIndicatorOn():
        gpio.setIndicatorOn()
    if task_thread is None or not task_thread.is_alive():
        task_thread = threading.Thread(target=eventLoop)
        task_thread.daemon = True
        task_thread.start()


def stopThread():
    global eventLoopActive
    if eventLoopActive:
        eventLoopActive = False
    if gpio.isIndicatorOn():
        gpio.setIndicatorOff()


# Toggle event loop whenever button is pressed
def buttonCallback():
    global eventLoopActive
    if eventLoopActive:
        stopThread()
        stopFireplace()
    else:
        startThread()

    
gpio.setButtonCallback(buttonCallback)


def startFireplace():
    if not gpio.isFireplaceOn():
        gpio.setFireplaceOn()
    if not ecobee.fanHoldActive:
        ecobee.setFanHold()


def stopFireplace():
    if gpio.isFireplaceOn():
        gpio.setFireplaceOff()
    if ecobee.fanHoldActive:
        ecobee.resumeProgram()


@app.route("/")
def home():
    summaryData = ecobee.getSummaryData()
    sensors = map(lambda sensor: ("-> " + sensor[0], sensor[1]),
                  summaryData['sensorList'])
    data = [
            ('Thread running', 'Yes' if eventLoopActive else 'No'),
            ('Runtime temp', summaryData['runtimeTemp']),
            *sensors,
            ('Desired heat', summaryData['desiredHeat']),
            ('Override desired temp', ecobee.overrideTargetTemp),
            ('Fireplace state', 'On' if gpio.isFireplaceOn() else 'Off'),
            ('Fan hold', 'On' if ecobee.fanHoldActive else 'Off')
           ]
    for sensor in sensors:
        data.append(sensor)
    return render_template('index.html',
                           data=data)


@app.route("/on")
def on():
    startFireplace()
    return "<p>On</p>"


@app.route("/off")
def off():
    stopFireplace()
    return "<p>Off</p>"


@app.route("/info")
def getInfo():
    return ecobee.getInfo()


@app.route("/sensors")
def getSensors():
    return ecobee.getSensors()


@app.route("/events")
def getEvents():
    return ecobee.getEvents()


@app.route("/currentTemp")
def getCurrentTemp():
    return render_template('simple.html', content=ecobee.getCurrentTemp())


@app.route("/authorize")
def authorize():
    ecobeePin = ecobee.authorize()
    return '<p>Enter this Pin into your ecobee \"My Apps\" section: <code>'\
           '{code}</code></p><p>Click here when done: '\
           '<a href="/completeAuthorization"><button>Done</button></a>'\
           .format(code=ecobeePin)


@app.route("/completeAuthorization")
def refreshToken():
    didSucceed = ecobee.completeAuthorization()
    resultText = 'Success' if didSucceed else 'Fail'
    return '<p>{resultText}</p>'.format(resultText=resultText)


@app.route("/start")
def start():
    startThread()
    return "<p>Thread will start</p>"


@app.route("/stop")
def stop():
    stopThread()
    return "<p>Thread will stop</p>"


@app.route("/override", methods=('GET', 'POST'))
def override():
    global forceRefresh
    if request.method == 'POST':
        override = None
        try:
            formVal = request.form['override']
            override = int(formVal) if formVal else None
        except Exception as e:
            print(e)

        if override:
            ecobee.setOverrideTargetTemp(override)
            flash("Set to {}".format(str(override)))
        else:
            ecobee.clearOverrideTargetTemp()
            flash("Cleared")

        forceRefresh = True

    return render_template('override.html',
                           currentOverride=ecobee.overrideTargetTemp)


@app.route("/stopoff", methods=('GET', 'POST'))
def stopoff():
    global eventLoopActive
    if request.method == 'POST':
        stopThread()
        stopFireplace()

    return render_template('stopoff.html')



def onExit(signal, frame):
    gpio.cleanup()
    sys.exit()


signal.signal(signal.SIGINT, onExit)


if __name__ == '__main__':
    app.run(
        host=config.get('Environment', 'Host', '127.0.0.1'),
        port=config.get('Environment', 'Port', '5000')
    )

