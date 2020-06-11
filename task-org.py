import re
import argparse
import calendar
from pathlib import Path
from datetime import datetime, date, timedelta

from modules import log
from modules import utils
from modules import config
from todo import Task, Todo, DailyTodo, WeeklyTodo, ArchiveTodo

# To add @recurring tag completion, add this line to  the
# \Packages\PlainTasks\PlainTasks.sublime-completions file:
# { "trigger": "r\t@recurring", "contents": "@recurring"}

global_config = config.get_config('global')
log_path = Path(global_config['paths']['log_path'])

script_name = utils.get_script_name(__file__)
config = config.get_config(script_name)
todo_path = Path(config['paths']['todo_path'])
backup_path = Path(config['paths']['backup_path'])
archive_path = Path(config['paths']['archive_path'])

logger = log.get_logger(script_name, log_path=log_path)

today = datetime.today().date()
tomorrow = today + timedelta(days=1)


def main(args):

  if args['test']:
    log.remove_file_handler(logger)

  todo_files = [f for f in todo_path.iterdir() if f.suffix == Todo.file_extension]
  cleanup_unused_files(todo_files, args['test'])

  # Create today's todo file
  today_todo = DailyTodo(today)
  create_file(today_todo, args['test'])

  # Create next week's todo file
  future_day = today + timedelta(days=7)
  next_week_first_day = WeeklyTodo.get_first_day_of_week(future_day)
  next_week_todo = WeeklyTodo(next_week_first_day)
  create_file(next_week_todo, args['test'])

  # Cleanup daily tasks
  today_todo = DailyTodo(today)
  day_files = [ fpath for fpath in todo_files if re.search(DailyTodo.fname_pattern, fpath.stem) ]
  day_todos = [ t for t in extract_todos(day_files, DailyTodo) if t.sdate <  today ]
  archive_fpath = get_fpath(ArchiveTodo.archive_fname, fpath=archive_path)
  try:
    update_todos(day_todos, today_todo, args['test'])
  except Exception as e:
    logger.exception(e)

  # Cleanup weekly tasks
  weekly_todo = WeeklyTodo(today)
  first_day_of_week = WeeklyTodo.get_first_day_of_week(today)
  week_files = [ fpath for fpath in todo_files if re.search(WeeklyTodo.fname_pattern, fpath.stem) ]
  week_todos = [ t for t in extract_todos(week_files, WeeklyTodo) if t.iso_week_number < WeeklyTodo.get_iso_week_number(today) ]
  try:
    update_todos(week_todos, weekly_todo, args['test'])
  except Exception as e:
    logger.exception(e)


def create_file(todo, test):
  fpath = get_fpath(todo.fname)
  if not fpath.exists():
    logger.info(f"creating file: '{fpath}'")
    write_todo(todo, fpath, test)
  else:
    logger.info(f"file '{fpath}' already exists")

def cleanup_unused_files(files, test):
  for fpath in files:
    try:
      file_line_count = len(open(fpath).readlines())
      if file_line_count < 2:
        if test: continue
        backup_or_delete(fpath, test)
    except Exception as e:
      logger.exception(e)

def update_todos(todos, current_todo, test):
  archive_todo = ArchiveTodo()
  current_fpath = get_fpath(current_todo.fname)
  load_todo(current_todo, current_fpath)
  archive_fpath = get_fpath(archive_todo.fname, fpath=archive_path)
  load_todo(archive_todo, archive_fpath)

  for todo in todos:
    for task in todo.tasks:
      if task.is_completed() and not task.recurring:
        is_weekly = isinstance(todo, WeeklyTodo)
        logger.info(f"archiving task: '{str(task).strip()}'")
        archive_todo.append(task, todo.sdate, is_weekly)
      else:
        if task.recurring:
          task = Task('pending', task.description, recurring=True)
        logger.info(f"moving task to current todo: '{str(task).strip()}'")
        current_todo.append(task)

    try:
      fpath = get_fpath(todo.fname)
      backup_or_delete(fpath, test)
    except Exception as e:
      logger.exception(e)

  try:
    write_todo(current_todo, current_fpath, test)
    write_todo(archive_todo, archive_fpath, test)
  except Exception as e:
    logger.exception(e)

def backup_or_delete(fpath, test, action='backup'):
  if action == 'backup':
    logger.info(f"moving '{fpath.name}' to backup folder '{backup_path}'")
    if test: return
    fpath.replace(backup_path / fpath.name)
  elif action == 'delete':
    logger.info(f"deleting '{fpath}'")
    if test: return
    fpath.unlink()
  else:
    raise ValueError("action must be either 'backup' or 'delete'")

def extract_todos(files, tclass):
  day_todos = []
  for fpath in files:
    try:
      todo = tclass()
      load_todo(todo, fpath)
      day_todos.append(todo)
    except Exception as e:
      logger.exception(e)
  return day_todos

def load_todo(todo, fpath):
  with open(fpath) as file:
    lines = file.readlines()
    todo.parse(lines)

def write_todo(todo, fpath, test=False):
  logger.info(f"writing file '{fpath}'")
  if test:
    logger.debug(str(todo))
    return
  try:
    with open(fpath, 'w') as file:
      file.write(str(todo))
  except Exception as e:
    logger.exception(e)

def get_fpath(fname, fpath=todo_path):
  return fpath / f'{fname}{Todo.file_extension}'


def get_parser():
  parser = argparse.ArgumentParser(
    description='Generate and manage ToDo files',
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    )
  parser.add_argument(
    '-t',
    '--test',
    action='store_true',
    help = 'Test run. No files will be moofied'
    )
  return parser


if __name__ == "__main__":
  parser = get_parser()
  args = vars(parser.parse_args())
  try:
    main(args)
  except Exception as e:
    logger.exception(e)
