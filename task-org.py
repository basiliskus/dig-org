import re
import argparse
import calendar
from pathlib import Path
from datetime import datetime, date, timedelta

from modules import log
from modules import utils
from modules import config
from todo import Task, Todo, TodoSection, DailyTodo, WeeklyTodo, ArchiveTodo

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

TODO_FEXT = '.todo'
TODAY_FNAME = 'today'
TOMORROW_FNAME = 'tomorrow'
CALENDAR_FNAME = 'calendar'
THIS_WEEK_FNAME = 'this-week'
NEXT_WEEK_FNAME = 'next-week'
ARCHIVE_FNAME = 'archive'


def main(args):

  if args['test'] or args['show']:
    log.remove_file_handler(logger)

  today_todo = DailyTodo(today)
  today_fpath = get_fpath(TODAY_FNAME)
  today_todo.load(today_fpath)

  weekly_todo = WeeklyTodo(today)
  weekly_fpath = get_fpath(THIS_WEEK_FNAME)
  weekly_todo.load(weekly_fpath)

  calendar_todo = ArchiveTodo()
  calendar_fpath = get_fpath(CALENDAR_FNAME)
  calendar_todo.load(calendar_fpath)

  archive_todo = ArchiveTodo()
  archive_fpath = get_fpath(ARCHIVE_FNAME, folder=archive_path)
  archive_todo.load(archive_fpath)

  if args['update']:
    update(today_todo, weekly_todo, calendar_todo, archive_todo)
    write(today_todo, today_fpath, args['test'])
    write(weekly_todo, weekly_fpath, args['test'])
    write(calendar_todo, calendar_fpath, args['test'])
    write(archive_todo, archive_fpath, args['test'])

  if args['show'] == 'today':
    show(today_todo)
  elif args['show'] == 'week':
    show(weekly_todo)
  elif args['show'] == 'calendar':
    show(calendar_todo)


def update(today_todo, weekly_todo, calendar_todo, archive_todo):
  # Transfer current tasks to today's todo
  logger.debug('updating calendar todo')
  for todo in calendar_todo.todos:
    if todo.sdate <= today:
      for task in todo.tasks:
        task.priority = 'today'
        today_todo.append(task)
      calendar_todo.todos.remove(todo)

  # Update daily tasks
  logger.debug('updating daily todo')
  today_todo.update(archive_todo)

  # Update weekly tasks
  logger.debug('updating weekly todo')
  weekly_todo.update(archive_todo)

def write(todo, fpath, test=False):
  logger.info(f"writing file '{fpath}'")
  if not test:
    try:
      todo.write(fpath)
    except Exception as e:
      logger.exception(e)
  else:
    logger.debug(str(todo))

def show(todo):
  logger.info(str(todo))

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

def get_fpath(fname, folder=todo_path):
  return folder / f'{fname}{TODO_FEXT}'


def get_parser():
  parser = argparse.ArgumentParser(
    description='Generate and manage ToDo files',
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    )
  parser.add_argument(
    '-u',
    '--update',
    action='store_true',
    help = 'Update tasks to current date and archive completed tasks'
    )
  parser.add_argument(
    '-s',
    '--show',
    choices = ['today', 'week', 'calendar' ],
    help = 'Show daily, weekly or calendar tasks'
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
