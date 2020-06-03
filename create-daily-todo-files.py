import re
import calendar
from pathlib import Path
from datetime import datetime, date, timedelta

from modules import log
from modules import utils
from modules import config


TODO_EXTENSION = '.todo'

DAY_FNAME_PATTERN = r'(\d+-\d+-\d+)'
DAY_ARCHIVE_FNAME = 'archive-daily'
DAY_FNAME_FORMAT = '%Y-%m-%d'
DAY_HEADER_FORMAT = '%m/%d/%Y'

WEEK_FNAME_PATTERN = r'(\d+-\d+)-week-(\d+)'
WEEK_ARCHIVE_FNAME = 'archive-weekly'
WEEK_FNAME_STRFTIME_FORMAT = '%Y-%m'
WEEK_HEADER_FORMAT = '%m/%d'

DONE_TAG = '@done'
RECURRING_TAG = '@recurring'
TASK_PATTERN = r'^\s*(\[[ x]\])\s*([^@]+)(@\w+)?\s*(' + DONE_TAG + r')?\s*(\(.+\))?$'
TASK_TIMESTAMP = r'(%y-%m-%d %H:%M)'

global_config = config.get_config('global')
log_path = Path(global_config['paths']['log_path'])

script_name = utils.get_script_name(__file__)
config = config.get_config(script_name)
todo_path = Path(config['paths']['todo_path'])
backup_path = Path(config['paths']['backup_path'])
archive_path = Path(config['paths']['archive_path'])

logger = log.get_logger(script_name, log_path=log_path)

today = datetime.today().date()
today_fname = today.strftime(DAY_FNAME_FORMAT)


def main():

  todo_files = [f for f in todo_path.iterdir() if f.suffix == TODO_EXTENSION]
  cleanup_unused_files(todo_files)

  # Create today's todo file
  today_fpath = get_fpath(today_fname)
  day_file_content = f"Day of {today.strftime(DAY_HEADER_FORMAT)}:\n"
  create_file(today_fpath, day_file_content)

  # Create next week's todo file
  future_day = today + timedelta(days=4)
  start_of_week = future_day - timedelta(days=future_day.weekday())
  end_of_week = start_of_week + timedelta(days=6)
  week_number = future_day.isocalendar()[1] - future_day.replace(day=1).isocalendar()[1] + 1
  week_fpath = todo_path / f"{future_day.strftime('%Y-%m')}-week-{week_number}{TODO_EXTENSION}"
  week_file_content = f"Week of {start_of_week.strftime('%m/%d')} - {end_of_week.strftime('%m/%d')}:\n"
  create_file(week_fpath, week_file_content)

  # Cleanup daily tasks
  day_files = [ fpath for fpath in todo_files if re.search(DAY_FNAME_PATTERN, fpath.stem) ]
  day_archive_fpath = get_fpath(DAY_ARCHIVE_FNAME, fpath=archive_path)
  get_day_date = lambda fpath: datetime.strptime(fpath.stem, DAY_FNAME_FORMAT).date()
  get_day_archive_header = lambda date: f"{date.strftime(DAY_HEADER_FORMAT)}:\n"
  get_day_current_fpath = lambda date: get_fpath(date.strftime(DAY_FNAME_FORMAT))
  try:
    archive_tasks(day_files, day_archive_fpath, today, get_day_date, get_day_archive_header, get_day_current_fpath)
  except Exception as e:
    logger.error(e)

  # Cleanup weekly tasks
  week_files = [ fpath for fpath in todo_files if re.search(WEEK_FNAME_PATTERN, fpath.stem) ]
  week_archive_fpath = get_fpath(WEEK_ARCHIVE_FNAME, fpath=archive_path)
  first_day_of_week = get_first_day_of_week(today)
  try:
    archive_tasks(week_files, week_archive_fpath, first_day_of_week, get_week_date, get_week_archive_header, get_week_current_fpath)
  except Exception as e:
    logger.error(e)


def create_file(fpath, content):
  if not fpath.exists():
    logger.debug(f"creating file: '{fpath}'")
    with open(fpath, 'w') as file:
      file.write(content)
  else:
    logger.debug(f"file '{fpath}' already exists")

def archive_tasks(relevant_files, archive_fpath, current_date, get_date, get_archive_header, get_current_fpath):

  current_fpath = get_current_fpath(current_date)

  for fpath in relevant_files:

    try:
      fdate = get_date(fpath)
    except Exception as e:
      logger.debug(f"not able to archive: '{fpath}'")
      logger.error(e)
      continue

    if (fdate < current_date):

      with open(archive_fpath, 'a') as archive_file, \
        open(current_fpath, 'a') as current_file:
        try:
          with open(fpath) as past_file:
            archive_first_line = True
            next(past_file) # ignore first line of file
            for line in past_file:
              task = parse_task(line)
              if task['is_checked'] and not task['has_recurring_tag']:
                # archive
                if archive_first_line:
                  try:
                    archive_file.write(get_archive_header(fdate))
                  except Exception as e:
                    logger.error(e)
                  archive_first_line = False
                logger.debug(f"archiving task: '{line.strip()}'")
                archive_file.write(line)
              else:
                # move task to current todo
                logger.debug(f"moving task to current todo: '{line.strip()}'")
                if task['has_recurring_tag']:
                  line = create_task_line(False, task['description'], task['has_recurring_tag'])
                current_file.write(line)
        except Exception as e:
          logger.debug(f"not able to archive: '{fpath}'")
          logger.error(e)
          continue

      try:
        logger.debug(f"moving '{fpath.name}' to backup folder '{backup_path}'")
        backup_or_delete(fpath)
      except Exception as e:
        logger.error(e)


def parse_task(line):
  match = re.search(TASK_PATTERN, line)
  if match and match[1] and match[2] :
    is_checked = (match[1] == "[x]")
    has_recurring_tag = (match[3] == RECURRING_TAG)
    has_done_tag = (match[4] == DONE_TAG)
    try:
      timestamp = datetime.strptime(match[5], TASK_TIMESTAMP)
    except:
      timestamp = None
    return { 'is_checked': is_checked, 'description': match[2].strip(), 'has_recurring_tag': has_recurring_tag, 'has_done_tag': has_done_tag, 'timestamp': timestamp }
  else:
    raise ValueError(f"could not parse task '{line}'")

def create_task_line(is_checked, description, has_recurring_tag=False, has_done_tag=False, timestamp=None):
  checkbox = '[x]' if is_checked else '[ ]'
  append_tags = f' {RECURRING_TAG}' if has_recurring_tag else ''
  append_tags += f' {DONE_TAG}' if has_done_tag else ''
  append_tags += f' { timestamp.strftime(TASK_TIMESTAMP)}' if timestamp else ''
  return f' {checkbox} {description}{append_tags}\n'

# def is_relevant_file(fname):
#   return fname in [ today_fname, day_archive_fname ]
#   return fname in [ today_fname, DAY_ARCHIVE_FNAME,  ]

def get_fpath(fname, fpath=todo_path):
  return fpath / f'{fname}{TODO_EXTENSION}'

def get_week_date(fpath):
  match = re.search(WEEK_FNAME_PATTERN, fpath.stem)
  if match:
    year_month = match[1]
    monthweek = int(match[2])
    first_day_month = datetime.strptime(year_month, WEEK_FNAME_STRFTIME_FORMAT).date()
    first_day_month_week = first_day_month.isocalendar()[1]
    return date.fromisocalendar(first_day_month.year, first_day_month_week + monthweek - 1, 1)
  else:
    raise ValueError(f"date could not be extracted from '{fpath}'")

def get_week_archive_header(pdate):
  weekday = calendar.weekday(pdate.year, pdate.month, pdate.day)
  sdate = get_first_day_of_week(pdate)
  edate = get_last_day_of_week(pdate)
  return f'{sdate.strftime(WEEK_HEADER_FORMAT)} - {edate.strftime(WEEK_HEADER_FORMAT)}:\n'

def get_first_day_of_week(pdate):
  weekday = calendar.weekday(pdate.year, pdate.month, pdate.day)
  fdate = pdate - timedelta(days=weekday)
  return fdate

def get_last_day_of_week(pdate):
  weekday = calendar.weekday(pdate.year, pdate.month, pdate.day)
  ldate = pdate + timedelta(days=6-weekday)
  return ldate

def get_week_current_fpath(pdate):
  week_month_day = pdate.strftime(WEEK_FNAME_STRFTIME_FORMAT)
  monthweek = get_week_number_of_month(pdate)
  return get_fpath(f'{week_month_day}-week-{monthweek}')

def get_week_number_of_month(pdate):
  return (pdate.isocalendar()[1] - pdate.replace(day=1).isocalendar()[1] + 1)

def backup_or_delete(fpath, action='backup'):
  if action == 'backup':
    fpath.replace(backup_path / fpath.name)
  elif action == 'delete':
    fpath.unlink()
  else:
    raise ValueError("action must be either 'backup' or 'delete'")

def archive(fpath):
  fpath.replace(archive_path / fpath.name)

def cleanup_unused_files(files):
  for fpath in files:
    file_line_count = len(open(fpath).readlines())
    if file_line_count < 2:
      logger.debug(f"moving '{fpath.name}' to backup folder '{backup_path}'")
      try:
        backup_or_delete(fpath)
      except Exception as e:
        logger.error(e)


if __name__ == "__main__":
  main()
