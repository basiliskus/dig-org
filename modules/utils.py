import os
from datetime import date, datetime

def get_script_name(fname):
  return os.path.splitext(os.path.basename(fname))[0]

def strip(string, rmv):
  for r in rmv:
    string = string.replace(r, '')
  return string

def get_date_from_unix_timestamp(uts):
  uts = int(uts[:10]) if len(uts) > 10 else int(uts)
  return datetime.fromtimestamp(uts)

def get_tag_from_category(cat):
  return cat.replace(' ', '-').lower()
