import argparse
import requests
from pathlib import Path

from modules import log
from modules import utils
from modules import config
from bookmark import Bookmark, BookmarkCollection


config = config.get_config('config')
log_path = Path(config['global']['log_path'])
bkm_md_fpath = Path(config['bkm-org']['bkm_md_fpath'])
bkm_json_fpath = Path(config['bkm-org']['bkm_json_fpath'])

script_name = utils.get_script_name(__file__)
logger = log.get_logger(script_name, log_path=log_path)


def main(args):

  bc = BookmarkCollection()
  bc.load_json(bkm_json_fpath)

  if args['validatelinks']:
    bc.validate()
    bc.write_json(bkm_json_fpath)

  if args['statuscode']:
    if args['statuscode'] != 1:
      print('\n'.join(bc.get_urls('status', args['statuscode'])))
    else:
      print(bc.get_grouped_bookmarks_str('status'))

  if args['tag']:
    if args['tag'] != 'all':
      print('\n'.join(bc.get_urls('tag', args['tag'])))
    else:
      print(bc.get_grouped_bookmarks_str('tag'))


def get_parser():
  parser = argparse.ArgumentParser(
    description='Bookmark file manager',
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    )
  parser.add_argument(
    '-vl',
    '--validate-links',
    dest = 'validatelinks',
    action='store_true',
    help = 'Validate links'
    ),
  parser.add_argument(
    '-sc',
    '--status-code',
    dest = 'statuscode',
    action='store',
    type=int,
    nargs='?',
    const=1,
    help = 'Get URLs by status code'
    ),
  parser.add_argument(
    '-t',
    '--tag',
    action='store',
    type=str,
    nargs='?',
    const='all',
    help = 'Get URLs by tag'
    )
  return parser


if __name__ == "__main__":
  parser = get_parser()
  args = vars(parser.parse_args())
  try:
    main(args)
  except Exception as e:
    logger.exception(e)
