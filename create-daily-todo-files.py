import re
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


def main():

  todo_files = [f for f in todo_path.iterdir() if f.suffix == Todo.file_extension]
  cleanup_unused_files(todo_files)

  # Create today's todo file
  today_todo = DailyTodo(today)
  create_file(today_todo)

  # Create next week's todo file
  future_day = today + timedelta(days=7)
  next_week_first_day = WeeklyTodo.get_first_day_of_week(future_day)
  next_week_todo = WeeklyTodo(next_week_first_day)
  create_file(next_week_todo)

  # Cleanup daily tasks
  today_todo = DailyTodo(today)
  day_files = [ fpath for fpath in todo_files if re.search(DailyTodo.fname_pattern, fpath.stem) ]
  day_todos = [ t for t in extract_todos(day_files, DailyTodo) if t.sdate <  today ]
  archive_fpath = get_fpath(ArchiveTodo.archive_fname, fpath=archive_path)
  try:
    update_todos(day_todos, today_todo)
  except Exception as e:
    logger.exception(e)

  # Cleanup weekly tasks
  weekly_todo = WeeklyTodo(today)
  first_day_of_week = WeeklyTodo.get_first_day_of_week(today)
  week_files = [ fpath for fpath in todo_files if re.search(WeeklyTodo.fname_pattern, fpath.stem) ]
  week_todos = [ t for t in extract_todos(week_files, WeeklyTodo) if t.iso_week_number < WeeklyTodo.get_iso_week_number(today) ]
  try:
    update_todos(week_todos, weekly_todo)
  except Exception as e:
    logger.exception(e)


def create_file(todo):
  fpath = get_fpath(todo.fname)
  if not fpath.exists():
    logger.debug(f"creating file: '{fpath}'")
    write_todo(todo, fpath)
  else:
    logger.debug(f"file '{fpath}' already exists")

def cleanup_unused_files(files):
  for fpath in files:
    try:
      file_line_count = len(open(fpath).readlines())
      if file_line_count < 2:
        logger.debug(f"moving '{fpath.name}' to backup folder '{backup_path}'")
        backup_or_delete(fpath)
    except Exception as e:
      logger.exception(e)

def update_todos(todos, current_todo):
  archive_todo = ArchiveTodo()
  current_fpath = get_fpath(current_todo.fname)
  load_todo(current_todo, current_fpath)
  archive_fpath = get_fpath(archive_todo.fname, fpath=archive_path)
  load_todo(archive_todo, archive_fpath)

  for todo in todos:
    for task in todo.tasks:
      if task.is_completed() and not task.is_recurring():
        logger.debug(f"archiving task: '{task.get_line().strip()}'")
        is_weekly = isinstance(todo, WeeklyTodo)
        archive_todo.append(task, todo.sdate, is_weekly)
      else:
        logger.debug(f"moving task to current todo: '{task.get_line().strip()}'")
        if task.is_recurring():
          task = Task('pending', task.description, recurring=True)
        current_todo.append(task)

    fpath = get_fpath(todo.fname)
    logger.debug(f"moving '{fpath.name}' to backup folder '{backup_path}'")
    try:
      backup_or_delete(fpath)
    except Exception as e:
      logger.exception(e)

  try:
    write_todo(current_todo, current_fpath)
    write_todo(archive_todo, archive_fpath)
  except Exception as e:
    logger.exception(e)

def backup_or_delete(fpath, action='backup'):
  if action == 'backup':
    fpath.replace(backup_path / fpath.name)
  elif action == 'delete':
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

def write_todo(todo, fpath):
  with open(fpath, 'w') as file:
    file.write(todo.get_string())

def get_fpath(fname, fpath=todo_path):
  return fpath / f'{fname}{Todo.file_extension}'


if __name__ == "__main__":
  main()
