import argparse
import requests
from pathlib import Path

from modules import log
from modules import utils
from modules import config
from bookmark import Bookmark, BookmarkCollection


config = config.get_config('config')
log_path = Path(config['global']['log_path'])

script_name = utils.get_script_name(__file__)
logger = log.get_logger(script_name, log_path=log_path)


def main(args):

  if args['bookmarkfile']:
    json_fpath = Path(args['bookmarkfile'])
  else:
    json_fpath = Path(config['bkm-org']['bkm_json_fpath'])

  md_fpath = json_fpath.with_suffix('.md')

  if args['findduplicates']:
    bc = BookmarkCollection()
    bc.load(md_fpath)
    print(bc.duplicate_urls())
    return

  bc = BookmarkCollection()
  bc.load(json_fpath)

  if args['validate']:
    if args['validate'] == 'bookmarks':
      bc.validate()
      bc.write_json(json_fpath)
    else:
      b = Bookmark(args['validate'])
      if b.verify():
        lr = b.last_request
        print(f'validated:\n connected: {lr.connected}\n status: {lr.status}\n redirect: {lr.redirect}\n title: {lr.title}\n')
      else:
        print('not able to validate')
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
    bcd.load(json_fpath)
    bcd.import_nbff(args['import'])
    bcd.write_json(json_fpath)
    return

  if args['add']:
    url = args['add'][0]
    tags = args['add'][1] if len(args['add']) > 1 else None
    if bc.add_url(url, tags):
      bc.write_json(json_fpath)
      print(f'{url}: successfully added to collection and saved at {json_fpath}')
    elif bc.add_tags(url, tags.split(',')):
      bc.write_json(json_fpath)
      print(f"{url}: successfully added tags '{tags}' to url and saved at {json_fpath}")
    else:
      print(f'{url}: not able to add url to collection')
    return

  if args['delete']:
    url = args['delete'][0]
    tag = args['delete'][1] if len(args['delete']) > 1 else None
    if tag:
      if bc.delete_tag(url, tag):
        bc.write_json(json_fpath)
        print(f"{url}: successfully deleted tag '{tag}' and saved at {json_fpath}")
      else:
        print(f"{url}: not able to delete tag '{tag}'")
      return
    if bc.delete_url(url):
      bc.write_json(json_fpath)
      print(f'{url}: successfully deleted from collection and saved at {json_fpath}')
    else:
      print(f'{url}: not able to delete url from collection')
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
    help = 'Specify bookmark file'
  ),
  parser.add_argument(
    '-v',
    '--validate',
    action='store',
    nargs='?',
    const='bookmarks',
    help = 'Validate urls. If not url is given, validate bookmark collection'
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
    help = 'Import Netscape Bookmark File'
  ),
  parser.add_argument(
    '-a',
    '--add',
    nargs='+',
    action='store',
    help = 'Add url and tags if provided (tags are separated by comma and without space). If url exists, adds tags to url'
  ),
  parser.add_argument(
    '-d',
    '--delete',
    nargs='+',
    action='store',
    help = 'Delete url or tag (if tag provided, url exists and has the tag)'
  )
  return parser


if __name__ == "__main__":
  parser = get_parser()
  args = vars(parser.parse_args())
  try:
    main(args)
  except Exception as e:
    logger.exception(e)
