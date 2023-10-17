import time
import threading
from gpio import GPIO
from ecobee import Ecobee
from configuration import config
from flask import Flask, render_template

app = Flask(__name__)
task_thread = None
TEMP_CHECK_DELAY_SEC = 180

# Global flag to control the scheduled task
allowEventLoop = True


def checkTemps():
    tempDiff = ecobee.getTempDifferential()

    # Current temperature is equal to or greater than desired
    if fireplace.isOn() and tempDiff > 0:
        fireplace.setOff()
        ecobee.resumeProgram()

    # Current temperature is a degree under desired
    if fireplace.isOff() and tempDiff < -10:
        fireplace.setOn()
        ecobee.setFanHold()


def eventLoop():
    global allowEventLoop
    seconds = 0
    while allowEventLoop:
        if (seconds % TEMP_CHECK_DELAY_SEC == 0):
            checkTemps()
            print("Current temp: {}".format(str(ecobee.getCurrentTemp())))
            seconds = 0
        seconds += 1
        time.sleep(1)
    print("Thread ended")


@app.route("/")
def home():
    return render_template('index.html',
                           currentTemp=ecobee.getCurrentTemp())


@app.route("/on")
def on():
    fireplace.setOn()
    return "<p>On</p>"


@app.route("/off")
def off():
    fireplace.setOff()
    return "<p>Off</p>"


@app.route("/info")
def getInfo():
    return ecobee.getInfo()


@app.route("/events")
def getEvents():
    return ecobee.getEvents()


@app.route("/currentTemp")
def getCurrentTemp():
    return ecobee.getCurrentTemp()


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
    global allowEventLoop, task_thread
    if not allowEventLoop:
        allowEventLoop = True
    if task_thread is None or not task_thread.is_alive():
        task_thread = threading.Thread(target=eventLoop)
        task_thread.daemon = True
        task_thread.start()
        return "<p>Thread will start</p>"
    else:
        return "<p>Thread will continue</p>"


@app.route("/stop")
def stop():
    global allowEventLoop
    if allowEventLoop:
        allowEventLoop = False
    return "<p>Thread will stop</p>"


def setup():
    global fireplace, ecobee

    if 'Environment' not in config.sections():
        raise Exception("Cannot find config data. Did you setup config.ini?")
    fireplace = GPIO()
    ecobee = Ecobee()


if __name__ == '__main__':
    setup()
    app.run(
        host=config.get('Environment', 'Host', '127.0.0.1'),
        port=config.get('Environment', 'Port', '5000')
    )
