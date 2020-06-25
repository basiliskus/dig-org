import re
import json
import argparse
import requests
from pathlib import Path

from modules import log
from modules import utils
from modules import config


config = config.get_config('config')
log_path = Path(config['global']['log_path'])
bookmarks_fpath = Path(config['bkm-org']['bookmarks_fpath'])

bkmval_fpath = log_path / 'bookmarks-validation.log'

script_name = utils.get_script_name(__file__)
logger = log.get_logger(script_name, log_path=log_path)

title_pattern = r'^(#+)\s+(.+)$'
link_pattern = r'^\*\s\[(.+)\]\s*\((https?:\/\/[\w\d./?=#]+)\)\s*$'

def main(args):

  with open(bookmarks_fpath, encoding='utf-8') as file:
    lines = file.readlines()

  if args['validatelinks']:
    vlinks = validate_links(lines)
    write_respose(vlinks)

  if args['findduplicates']:
    dup = find_duplicates(lines)
    logger.debug(dup)


def find_duplicates(lines):
  urls = get_urls(lines)
  return set([u for u in urls if urls.count(u) > 1])

def get_urls(lines):
  urls = []
  for line in lines:
    link_match = re.search(link_pattern, line)
    if not link_match: continue
    urls.append(link_match[2])
  return urls

def validate_links(lines):
  urls = get_urls(lines)
  response = {}
  for url in urls:
    status = str(validate_url(url))
    if status in response:
      logger.debug(f"adding '{url}' to status '{status}'")
      response[status].append(url)
    else:
      logger.debug(f"creating '{status}' and adding '{url}'")
      response[status] = [ url ]
  return response

def write_respose(vlinks, ftype='text'):
  if ftype == 'text':
    lines = []
    for code in sorted(vlinks.keys()):
      try:
        code_name = requests.status_codes._codes[code][0]
        lines.append(f'{code_name} ({code}):')
      except:
        lines.append(f'{code}:')
      for link in vlinks[code]:
        lines.append(f'  {link}')
    write_lines(bkmval_fpath, lines)

def write_lines(fpath, lines):
  with open(fpath, 'w') as file:
    file.write('\n'.join(lines))

def validate_url(url):
  try:
    request = requests.get(url)
    status = request.status_code
  except Exception as e:
    if hasattr(e, 'message'):
      status = e.message
    else:
      status = str(e)
  return status


def get_parser():
  parser = argparse.ArgumentParser(
    description='Bookmark file manager',
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    )
  parser.add_argument(
    '-vl',
    '--validatelinks',
    action='store_true',
    help = 'Validate links'
    ),
  parser.add_argument(
    '-d',
    '--findduplicates',
    action='store_true',
    help = 'Find duplicates'
    )
  return parser


if __name__ == "__main__":
  parser = get_parser()
  args = vars(parser.parse_args())
  try:
    main(args)
  except Exception as e:
    logger.exception(e)
