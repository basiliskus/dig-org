import configparser

CONFIG_EXTENSION = '.ini'
CONFIG_PATH = 'config/'

def get_config(fname):
  config = configparser.ConfigParser()
  config.read(f'{CONFIG_PATH}{fname}{CONFIG_EXTENSION}')
  return config
