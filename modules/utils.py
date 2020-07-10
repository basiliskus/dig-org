import os
from datetime import date, datetime

def get_script_name(fname):
  return os.path.splitext(os.path.basename(fname))[0]

def strip(string, chars):
  for c in chars:
    string = string.replace(c, '')
  return string

def escape(string, chars):
  for c in chars:
    string = string.replace(c, f'\\{c}')
  return string

def get_date_from_unix_timestamp(uts):
  uts = int(uts[:10]) if len(uts) > 10 else int(uts)
  return datetime.fromtimestamp(uts)

def get_tag_from_category(cat):
  return cat.replace(' ', '-').lower()

def get_category_hierarchy_str(cats):
  return ' > '.join(cats)
