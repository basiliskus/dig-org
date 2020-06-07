import re
import calendar
from pathlib import Path
from datetime import datetime, date, timedelta

DONE_TAG = '@done'
RECURRING_TAG = '@recurring'
WEEKLY_TAG = '@weekly'

TASK_PATTERN = r'^\s*(\[[ x]\])\s*([^@]+)(@\w+)?\s*(' + DONE_TAG + r')?\s*(\(.+\))?$'
TASK_TIMESTAMP = r'(%y-%m-%d %H:%M)'

DAY_HEADER_FORMAT = 'Day of %m/%d/%Y:'
WEEK_HEADER_FORMAT = '%m/%d'

today = datetime.today().date()


class Task:
  def __init__(self, status='pending', description='', tags=None, timestamp=None, priority=None, recurring=False, archived=False):
    self.status = status
    self.description = description
    self.tags = tags if tags is not None else []
    self.timestamp = timestamp
    if priority: self.tags.append(f'@{priority}')
    if recurring: self.tags.append(RECURRING_TAG)
    self.archived = archived
    self.checkbox = {
      'pending': '[ ]',
      'completed': '[x]',
      'cancelled': '[-]'
    }

  def parse(self, line):
    match = re.search(TASK_PATTERN, line)
    if match and match[1] and match[2] :
      self.status = list(self.checkbox.keys())[list(self.checkbox.values()).index(match[1])]
      self.description = match[2].strip()
      self.tags += [ match[3] ] if match[3] else []
      self.tags += [ match[4] ] if match[4] else []
      try:
        self.timestamp = datetime.strptime(match[5], TASK_TIMESTAMP)
      except:
        pass
    else:
      raise ValueError(f"could not parse task '{line}'")

  def get_line(self):
    checkbox = self.checkbox[self.status]
    tags = ' ' + ' '.join(self.tags) if len(self.tags) > 0 else ''
    timestamp = f" {self.timestamp.strftime(TASK_TIMESTAMP)}" if self.timestamp else ''
    return f" {checkbox} {self.description}{tags}{timestamp}\n"

  def is_completed(self):
    return self.status == 'completed'

  def is_recurring(self):
    return RECURRING_TAG in self.tags


class Todo:

  file_extension = '.todo'
  header_date_format = '%m/%d/%Y'
  header_date_pattern = r'(\d{2}/\d{2}/\d{4})'

  def __init__(self, sdate=None):
    self._header = ''
    self._sdate = sdate
    self.tasks = []

  def parse(self, lines):
    first_line = True
    for line in lines:
      line = line.strip()
      if not first_line:
        task = Task()
        task.parse(line)
        self.tasks.append(task)
      else:
        self._header = line
        first_line = False

  def append(self, task):
    self.tasks.append(task)

  def get_string(self):
    header = self.get_header_string()
    tasks = self.get_tasks_string()
    return header + tasks

  def get_header_string(self):
    return f'{self.header}\n'

  def get_tasks_string(self):
    task_lines = [ task.get_line() for task in self.tasks]
    return ''.join(task_lines)


class DailyTodo(Todo):

  header_format = 'Day of {}:'
  fname_format = '%Y-%m-%d'
  fname_pattern = r'(\d+-\d+-\d+)'

  @property
  def header(self):
    if self._header:
      return self._header
    if self._sdate:
      return self._sdate.strftime(self.header_format.format(self.header_date_format))
    raise ValueError('no header defined')

  @property
  def sdate(self):
    if self._sdate:
      return self._sdate
    if self._header:
      pattern = self.header_format.format(self.header_date_pattern)
      match = re.search(pattern, self._header)
      if match:
        return datetime.strptime(match[1], self.header_date_format).date()
    return None

  @property
  def fname(self):
    return self.sdate.strftime(self.fname_format)

  @staticmethod
  def parse_fpath(fpath):
    return datetime.strptime(fpath.stem, self.fname_format).date()


class WeeklyTodo(Todo):

  header_format = 'Week of {} - {}:'
  fname_date_format = '%Y-%m'
  fname_format = '{}-week-{}'
  fname_pattern = r'(\d+-\d+)-week-(\d+)'

  @property
  def header(self):
    if self._header:
      return self._header
    if self._sdate:
      return self.header_format.format(self._sdate.strftime(self.header_date_format), self.edate.strftime(self.header_date_format))
    return None

  @property
  def sdate(self):
    if self._sdate:
      return self._sdate
    if self._header:
      pattern = self.header_format.format(self.header_date_pattern, self.header_date_pattern)
      match = re.search(pattern, self._header)
      if match:
        return datetime.strptime(match[1], self.header_date_format).date()
    return None

  @property
  def edate(self):
    return self.sdate + timedelta(days=6) if self.sdate else None

  @property
  def fname(self):
    return self.fname_format.format(self.sdate.strftime(self.fname_date_format), self.month_week_number)

  @property
  def month_week_number(self):
    return self.get_month_week_number(self.sdate)

  @property
  def iso_week_number(self):
    return self.get_iso_week_number(self.sdate)

  @staticmethod
  def get_iso_week_number(pdate):
    return pdate.isocalendar()[1]

  @staticmethod
  def get_month_week_number(pdate):
    return pdate.isocalendar()[1] - pdate.replace(day=1).isocalendar()[1] + 1

  @staticmethod
  def get_first_day_of_week(pdate):
    weekday = calendar.weekday(pdate.year, pdate.month, pdate.day)
    fdate = pdate - timedelta(days=weekday)
    return fdate


class ArchiveTodo():

  header_format = '%m/%d/%Y:'
  header_pattern = r'(\d{2}/\d{2}/\d{4}:)'
  archive_fname = 'archive'

  def __init__(self):
    self.todos = []

  def parse(self, lines):
    first_line = True
    for line in lines:
      match = re.search(self.header_pattern, line)
      if match:
        if not first_line:
          self.todos.append(todo)
        else:
          first_line = False
        tdate = datetime.strptime(match[1], self.header_format).date()
        todo = DailyTodo(tdate)
      else:
        task = Task()
        task.parse(line)
        todo.tasks.append(task)
    self.todos.append(todo)

  def get_string(self):
    svalue = ''
    for todo in sorted(self.todos, key=lambda t: t.sdate):
      header = todo.sdate.strftime(self.header_format)
      svalue += f'{header}\n'
      svalue += todo.get_tasks_string()
    return svalue

  def append(self, task, pdate, is_weekly=False):
    if is_weekly:
      task.tags.insert(0, WEEKLY_TAG)
    if task.timestamp:
      pdate = task.timestamp.date()
    todos_on_date = [ t for t in self.todos if t.sdate == pdate ]
    if len(todos_on_date) > 0:
      todos_on_date[0].append(task)
    else:
      todo = DailyTodo(pdate)
      todo.append(task)
      self.todos.append(todo)

  @property
  def fname(self):
    return self.archive_fname;
