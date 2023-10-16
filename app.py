import RPi.GPIO as GPIO
import configparser
from flask import Flask

PIN = 11
CONFIG_FILENAME = 'config.ini'

# Setup
config = configparser.ConfigParser()
config.read(CONFIG_FILENAME)
app = Flask(__name__)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(PIN, GPIO.OUT)
pinState = 0

def setOn(on):
    global pinState
    pinState = on
    GPIO.output(PIN, pinState)



@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/on")
def on():
    setOn(True)
    return "<p>On</p>"

@app.route("/off")
def off():
    setOn(False)
    return "<p>Off</p>"

@app.route("/config")
def conf():
    testval=config['Auth']['Test']
    return "<p>" + testval + "</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0')

