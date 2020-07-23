import argparse
from pathlib import Path

from modules import log
from modules import utils
from modules import config


config = config.get_config('config')
log_path = Path(config['global']['log_path'])

script_name = utils.get_script_name(__file__)
logger = log.get_logger(script_name, log_path=log_path)


def main(args):
  print('this is a template')


def get_parser():
  parser = argparse.ArgumentParser(
      description='Template script description',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  parser.add_argument(
      '-t',
      '--test',
      action='store_true',
      help='Test run. No files will be modified'
  )
  return parser


if __name__ == "__main__":
  parser = get_parser()
  args = vars(parser.parse_args())
  try:
    main(args)
  except Exception as e:
    logger.exception(e)
