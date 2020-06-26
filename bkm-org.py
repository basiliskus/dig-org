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

bkm_val_fpath = log_path / 'bookmarks-validation.log'
bkm_red_fpath = log_path / 'bookmarks-validation-redirect.log'

script_name = utils.get_script_name(__file__)
logger = log.get_logger(script_name, log_path=log_path)

title_pattern = r'^(#+)\s+(.+)$'
link_pattern = r'^\*\s\[(.+)\]\s*\((https?:\/\/[\w\d./?=#]+)\)\s*$'


def main(args):

  bc = BookmarkCollection()
  bc.load_json(bkm_json_fpath)

  if args['validatelinks']:
    bc.validate()
    bc.write_json(bkm_json_fpath)

  if args['statuscode']:
    r = get_urls(bc, args['statuscode'])
    print(r)


def get_urls(bc, status):
  if status != 1:
    urls = [ b.url for b in bc.get_bookmarks(status) ]
    return '\n'.join(urls)
  else:
    response = []
    codes = list(set([ b.last_request.status for b in bc.bookmarks if b.last_request.status ]))
    for code in sorted(codes):
      if code in requests.status_codes._codes:
        code_name = requests.status_codes._codes[code][0]
        response.append(f'{code} ({code_name}):')
      else:
        response.append(f'{code}:')
      for b in bc.get_bookmarks(code):
        response.append(f'  {b.url}')
    return '\n'.join(response)


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
    '-sc',
    '--statuscode',
    action='store',
    type=int,
    nargs='?',
    const=1,
    help = 'Check status codes'
    )
  return parser


if __name__ == "__main__":
  parser = get_parser()
  args = vars(parser.parse_args())
  try:
    main(args)
  except Exception as e:
    logger.exception(e)
