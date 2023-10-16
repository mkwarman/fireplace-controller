import gpio
import ecobee
from configuration import config
from flask import Flask

app = Flask(__name__)


def setup():
    global fireplace, ecobee

    if 'Environment' not in config.sections():
        raise Exception("Cannot find config data. Did you setup config.ini?")
    fireplace = gpio.GPIO()
    ecobee = ecobee.Ecobee()


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/on")
def on():
    fireplace.setOn()
    return "<p>On</p>"


@app.route("/off")
def off():
    fireplace.setOff()
    return "<p>Off</p>"


@app.route("/info")
def conf():
    return ecobee.getInfo()


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


if __name__ == '__main__':
    setup()
    app.run(
        host=config.get('Environment', 'Host', '127.0.0.1'),
        port=config.get('Environment', 'Port', '5000')
    )
