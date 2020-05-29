import os

def get_script_name(fname):
  return os.path.splitext(os.path.basename(fname))[0]
