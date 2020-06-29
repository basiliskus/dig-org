import argparse
import requests
from pathlib import Path

from modules import log
from modules import utils
from modules import config
from bookmark import Bookmark, BookmarkCollection


config = config.get_config('config')
log_path = Path(config['global']['log_path'])
json_fpath = Path(config['bkm-org']['bkm_json_fpath'])

script_name = utils.get_script_name(__file__)
logger = log.get_logger(script_name, log_path=log_path)


def main(args):

  if args['bookmarkfile']:
    json_fpath = Path(args['bookmarkfile'])

  md_fpath = json_fpath.with_suffix('.md')

  if args['findduplicates']:
    bc = BookmarkCollection()
    bc.load(md_fpath)
    print(bc.duplicate_urls())
    return

  bc = BookmarkCollection()
  bc.load(json_fpath)

  if args['validatelinks']:
    bc.validate()
    bc.write_json(json_fpath)
    return

  if args['list']:

    if args['list'][0] == 'status':
      if len(args['list']) > 1:
        print('\n'.join(bc.get_urls('status', int(args['list'][1]))))
      else:
        print(bc.get_grouped_bookmarks_str('status'))
      return

    if args['list'][0] == 'tag':
      if len(args['list']) > 1:
        print('\n'.join(bc.get_urls('tag', args['list'][1])))
      else:
        print(bc.get_grouped_bookmarks_str('tag'))
      return

    if args['list'][0] == 'created':
      if len(args['list']) > 1:
        print('\n'.join(bc.get_urls('created', args['list'][1])))
      else:
        print(bc.get_grouped_bookmarks_str('created'))
      return

  if args['update']:
    if args['update'] == 'url':
      bc.update_urls()
      bc.write_json(json_fpath)
    if args['update'] == 'title':
      bc.update_titles()
      bc.write_json(json_fpath)
    elif args['update'] == 'md':
      bc.write_md(json_fpath.with_suffix('.md'))
    elif args['update'] == 'json':
      bc.load(md_fpath)
      bc.write_json(md_fpath.with_suffix('.json'))
    return

  if args['import']:
    bcd = BookmarkCollection()
    bcd.import_nbff(args['import'])
    bcd.write_json(json_fpath)
    return


def get_parser():
  parser = argparse.ArgumentParser(
    description='Bookmark file manager',
    formatter_class = argparse.RawTextHelpFormatter
  )
  parser.add_argument(
    '-f',
    '--bookmark-file',
    dest = 'bookmarkfile',
    action='store',
    type=str,
    help = 'Specify bookmark file'
  ),
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
    '-l',
    '--list',
    action='store',
    nargs='+',
    help = """List urls by property:
  'status':
    0: returns urls which failed to connect
    10: returns urls with unknown status
    none: returns all urls grouped by status
  'tag': return urls by tag
    none: return all urls grouped by tag
  'created': return urls by creation date with format 'yyyy-mm-dd'
    """
  ),
  parser.add_argument(
    '-u',
    '--update',
    action='store',
    choices = [ 'url', 'title', 'md', 'json' ],
    help = 'Update json file'
  ),
  parser.add_argument(
    '-i',
    '--import',
    action='store',
    type=str,
    help = 'Import Netscape Bookmark File'
  )
  return parser


if __name__ == "__main__":
  parser = get_parser()
  args = vars(parser.parse_args())
  try:
    main(args)
  except Exception as e:
    logger.exception(e)
