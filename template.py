from modules import log
from modules import utils
from modules import config
from modules import aparser

script_name = utils.get_script_name(__file__)
config = config.get_config(script_name)
logger = log.get_logger(script_name)

def main(args):
  print('this is a template')

if __name__ == "__main__":
  args = aparser.get_args()
  main(args)
