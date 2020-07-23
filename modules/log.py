import logging
from logging.handlers import TimedRotatingFileHandler

LOG_EXTENSION = '.log'


def get_logger(fname, log_path='logs', file_log_level='DEBUG', console_log_level='INFO', file_handler_type=None):

  date_format = '%Y/%m/%d %H:%M:%S'
  fh_format = '[%(asctime)s][%(levelname)s][%(funcName)s] %(message)s'
  fh_suffix = '%Y%m%d'
  sh_format = '%(message)s'

  logger = logging.getLogger(fname)
  logger.setLevel(logging.DEBUG)

  if console_log_level is not None:
    # create console handler
    sh = logging.StreamHandler()
    sh.setLevel(getattr(logging, console_log_level))
    sh.setFormatter(logging.Formatter(sh_format, date_format))
    logger.addHandler(sh)

  if file_log_level is not None:
    # create file handler
    log_fpath = f'{log_path}/{fname}{LOG_EXTENSION}'
    if file_handler_type == 'rotating':
      fh = TimedRotatingFileHandler(log_fpath, when='midnight', encoding='utf-8')
      fh.suffix = fh_suffix
    else:
      fh = logging.FileHandler(log_fpath, encoding='utf-8')
    fh.setLevel(getattr(logging, file_log_level))
    fh.setFormatter(logging.Formatter(fh_format, date_format))
    logger.addHandler(fh)

  return logger


def remove_file_handler(logger):
  fhandler = next(h for h in logger.handlers if isinstance(h, (logging.FileHandler, TimedRotatingFileHandler)))
  logger.handlers.remove(fhandler)
