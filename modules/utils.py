import os

def get_script_name(fname):
  return os.path.splitext(os.path.basename(fname))[0]

def strip(string, rmv):
  for r in rmv:
    string = string.replace(r, '')
  return string
