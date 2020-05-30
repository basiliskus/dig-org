from pathlib import Path

from modules import log
from modules import utils
from modules import config
from modules import aparser

global_config = config.get_config('global')
log_path = Path(global_config['paths']['log_path'])

script_name = utils.get_script_name(__file__)
logger = log.get_logger(script_name, log_path=log_path)

def main(args):
  print('this is a template')

if __name__ == "__main__":
  args = aparser.get_args()
  main(args)
