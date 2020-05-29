import logging

LOG_EXTENSION = '.log'

def get_logger(fname, log_path='logs', level=logging.INFO):
  logger = logging.getLogger()
  logger.setLevel(level)

  sh = logging.StreamHandler()
  logger.addHandler(sh)

  datefmt = '%Y/%m/%d %H:%M:%S'
  fhformat = '[%(asctime)s][%(levelname)s] %(message)s'
  log_fpath = f'{log_path}/{fname}{LOG_EXTENSION}'
  fh = logging.FileHandler(log_fpath)
  fh.setFormatter(logging.Formatter(fhformat, datefmt))
  logger.addHandler(fh)

  return logger
