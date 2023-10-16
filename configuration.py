import configparser

CONFIG_FILENAME = 'config.ini'


class Config():
    config = None

    def __init__(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILENAME)
        self.config = config

    def sections(self):
        return self.config.sections()

    def get(self, section, option, default):
        if section in self.config and option in self.config[section]:
            return self.config[section][option]
        return default


config = Config()
