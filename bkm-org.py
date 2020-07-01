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
    if not json_fpath.exists():
      json_fpath.touch()
  else:
    json_fpath = Path(config['bkm-org']['bkm_json_fpath'])

  if args['update']:
    utype = args['update']
    bc = BookmarkCollection(json_fpath)
    update_bookmarks(bc, utype)
    return

  if args['import']:
    itype = args['import'][0]
    fpath = args['import'][1]
    bc = BookmarkCollection()
    if json_fpath.stat().st_size > 0:
      bc.load(json_fpath)
    import_bookmarks(bc, itype, fpath, json_fpath)
    return

  if args['list']:
    bc = BookmarkCollection(json_fpath)
    ltype = args['list'][0]
    value = args['list'][1] if len(args['list']) > 1 else None
    if value:
      urls = bc.get_urls(ltype, value)
      if should_print(args):
        print_list(urls)
        return
    else:
      grouped_urls = bc.get_grouped_urls(ltype)
      if should_print(args):
        print_dict(grouped_urls)
        return

  if args['validate']:
    bc = BookmarkCollection(json_fpath)
    if urls:
      for u in urls:
        validate_url(bc, u)
        print()
    else:
      url = args['validate']
      if url == 'collection':
        bc.validate()
        bc.write()
      else:
        validate_url(bc, url)
    return

  if args['add']:
    url = args['add'][0]
    tags = args['add'][1].split(',') if len(args['add']) > 1 else None
    bc = BookmarkCollection(json_fpath)
    add_urls_andor_tags(bc, url, tags)
    return

  if args['delete']:
    bc = BookmarkCollection(json_fpath)
    if urls:
      for u in urls:
        delete_url(bc, u)
    else:
      url = args['delete'][0]
      tag = args['delete'][1] if len(args['delete']) > 1 else None
      if tag:
        delete_tag(bc, url, tag)
      else:
        delete_url(bc, url)
    return


def should_print(args):
  return args['validate'] is None and args['delete'] is None

def validate_url(bc, url):
  b = Bookmark(url)
  if b.verify():
    print_bookmark(b)
  else:
    print('not able to validate')

def print_bookmark(b):
  print(f"""url: {b.url}
connected: {b.last_request.connected}
status: {b.last_request.status}
title: {b.last_request.title}
redirect: {b.last_request.redirect}""")

def print_list(l):
  print('\n'.join(l))

def print_dict(d):
  for key in sorted(d.keys()):
    print(f'{key}:')
    for url in d[key]:
      print(f'  {url}')

def update_bookmarks(bc, utype):
  if utype == 'url':
    bc.update_urls()
    bc.write()
  elif utype == 'title':
    bc.update_titles()
    bc.write()
  elif utype == 'md':
    bc.write_md()
  elif utype == 'json':
    bc.import_md()
    bc.write_json()

def import_bookmarks(bc, itype, input, output):
  if itype == 'nbff':
    bc.import_nbff(input)
  elif itype == 'insta':
    bc.import_instapaper(input)
  bc.write(output)

def add_urls_andor_tags(bc, url, tags):
  if bc.add_url(url, tags):
    bc.write()
    print(f'{url}: successfully added to collection and saved at {bc.fpath}')
  elif bc.add_tags(url, tags):
    bc.write()
    print(f"{url}: successfully added tags '{tags}' to url and saved at {bc.fpath}")
  else:
    print(f'{url}: not able to add url to collection')

def delete_tag(bc, url, tag):
  if bc.delete_tag(url, tag):
    bc.write()
    print(f"{url}: successfully deleted tag '{tag}' and saved at {bc.fpath}")
  else:
    print(f"{url}: not able to delete tag '{tag}'")

def delete_url(bc, url):
  if bc.delete_url(url):
    bc.write()
    print(f'{url}: successfully deleted from collection and saved at {bc.fpath}')
  else:
    print(f'{url}: not able to delete url from collection')


def get_parser():
  parser = argparse.ArgumentParser(
    description = 'Bookmark file manager',
    formatter_class = argparse.RawTextHelpFormatter
  )
  parser.add_argument(
    '-f',
    '--bookmark-file',
    dest = 'bookmarkfile',
    action = 'store',
    help = 'Specify bookmark file'
  ),
  parser.add_argument(
    '-v',
    '--validate',
    action = 'store',
    nargs = '?',
    const = 'collection',
    help = 'Validate urls. If not url is given, validate bookmark collection'
  ),
  parser.add_argument(
    '-l',
    '--list',
    action = 'store',
    nargs = '+',
    help = """List urls by property:
  'status':
    0: returns urls which failed to connect
    10: returns urls with unknown status
    none: returns all urls grouped by status
  'tag': return urls by tag
    none: return all urls grouped by tag
  'created': return urls by creation date with format 'yyyy-mm-dd'"""
  ),
  parser.add_argument(
    '-u',
    '--update',
    action = 'store',
    choices = [ 'url', 'title', 'md', 'json' ],
    help = 'Update json file'
  ),
  parser.add_argument(
    '-i',
    '--import',
    action = 'store',
    nargs = 2,
    help = """Import bookmarks from:
  nbff: Netscape Bookmark File format
  insta: Instapaper"""
  ),
  parser.add_argument(
    '-a',
    '--add',
    nargs = '+',
    action = 'store',
    help = 'Add url and tags if provided (tags are separated by comma and without space). If url exists, adds tags to url'
  ),
  parser.add_argument(
    '-d',
    '--delete',
    nargs = '?',
    const = 'piped_urls',
    action = 'store',
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
