import argparse
import requests
from pathlib import Path

from modules import log
from modules import utils
from modules import config
from bookmark import Bookmark, BookmarkCollection


config = config.get_config('config')
log_path = Path(config['global']['log_path'])
md_fpath = Path(config['bkm-org']['bkm_md_fpath'])
json_fpath = Path(config['bkm-org']['bkm_json_fpath'])

script_name = utils.get_script_name(__file__)
logger = log.get_logger(script_name, log_path=log_path)


def main(args):

  if args['findduplicates']:
    bc = BookmarkCollection()
    bc.load_md(md_fpath)
    print(bc.duplicate_urls())
    return

  bc = BookmarkCollection()
  bc.load_json(json_fpath)

  if args['validatelinks']:
    bc.validate()
    bc.write_json(json_fpath)
    return

  if not args['statuscode'] is None:
    if args['statuscode'] != 1:
      print('\n'.join(bc.get_urls('status', args['statuscode'])))
    else:
      print(bc.get_grouped_bookmarks_str('status'))
    return

  if args['tag']:
    if args['tag'] != 'all':
      print('\n'.join(bc.get_urls('tag', args['tag'])))
    else:
      print(bc.get_grouped_bookmarks_str('tag'))
    return

  if args['update']:
    if args['update'] == 'url':
      bc.update_urls()
      bc.write_json(json_fpath)
    elif args['update'] == 'md':
      bc.write_md(md_fpath)
    elif args['update'] == 'json':
      bc.load_md(md_fpath)
      bc.write_json(json_fpath)
    return


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
    '-fd',
    '--find-duplicates',
    dest = 'findduplicates',
    action='store_true',
    help = 'Find duplicates in md file'
  ),
  parser.add_argument(
    '-sc',
    '--status-code',
    dest = 'statuscode',
    action='store',
    type=int,
    nargs='?',
    const=1,
    help = 'Get URLs by status code. Use 0 to get URLs which failed to connect'
  ),
  parser.add_argument(
    '-t',
    '--tag',
    action='store',
    type=str,
    nargs='?',
    const='all',
    help = 'Get URLs by tag'
  ),
  parser.add_argument(
    '-u',
    '--update',
    action='store',
    choices = [ 'url', 'md', 'json' ],
    help = 'Update json file'
  )
  return parser


if __name__ == "__main__":
  parser = get_parser()
  args = vars(parser.parse_args())
  try:
    main(args)
  except Exception as e:
    logger.exception(e)
