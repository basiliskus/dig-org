import re
import calendar
# from enum import Enum
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

statusd = {
  'pending': '[ ]',
  'completed': '[x]',
  'cancelled': '[-]'
}

priorityd = {
  'today': 1,
  'critical': 2,
  'high': 3,
  'low': 4,
  'default': 5
}

# class Priority(Enum):
#   today = 1
#   critical = 2
#   high = 3
#   low = 4

#   def __str__(self):
#     return f'@{self.name}'

# class Tag:
#   def __init__(self, tag):
#     _name = tag.name if isinstance(tag, Priority) else tag

#   def __str__(self):
#     return f'@{self._name}'

class Task:
  def __init__(self, status='pending', description='', tags=None, timestamp=None, priority='default', recurring=False, archived=False):
    self.status = status
    self.description = description
    self.tags = tags if tags is not None else []
    self.timestamp = timestamp
    self.priority = priority
    self.recurring = recurring
    self.archived = archived

  def __str__(self):
    tags = ' ' + ' '.join(self.tags) if len(self.tags) > 0 else ''
    priority = f' @{self.priority}' if self.priority and self.priority != 'default' else ''
    recurring = f' {RECURRING_TAG}' if self.recurring else ''
    done = f' {DONE_TAG}' if self.status == 'completed' else ''
    timestamp = f' {self.timestamp.strftime(TASK_TIMESTAMP)}' if self.timestamp else ''
    return f' {statusd[self.status]} {self.description}{tags}{priority}{recurring}{done}{timestamp}\n'

  def parse(self, line):
    match = re.search(TASK_PATTERN, line)
    if match and match[1] and match[2] :
      self.status = list(statusd.keys())[list(statusd.values()).index(match[1])]
      self.description = match[2].strip()
      self._parse_tag(match[3])
      self._parse_tag(match[4])
      try:
        self.timestamp = datetime.strptime(match[5], TASK_TIMESTAMP)
      except:
        pass
    else:
      raise ValueError(f"could not parse task '{line}'")

  def is_completed(self):
    return self.status == 'completed'

  def _parse_tag(self, tag):
    if not tag: return
    if tag[1:] in priorityd.keys():
      self.priority = tag[1:]
      return
    if tag == DONE_TAG:
      self.status = 'completed'
      return
    if tag == RECURRING_TAG:
      self.recurring = True
      return
    self.tags.append(tag)


class Todo:

  file_extension = '.todo'
  header_date_format = '%m/%d/%Y'
  header_date_pattern = r'(\d{2}/\d{2}/\d{4})'

  def __init__(self, sdate=None):
    self._header = ''
    self._sdate = sdate
    self.tasks = []

  def __str__(self):
    header = self.get_header_string()
    tasks = self.get_tasks_and_sections_string(sort='priority')
    return header + tasks

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

  def get_header_string(self):
    return f'{self.header}\n'

  def get_tasks_string(self):
    return ''.join([ str(task) for task in self.tasks ])

  def get_tasks_and_sections_string(self, sort=None):
    tasks = sorted(self.tasks, key=lambda t: priorityd[t.priority]) if sort == 'priority' else self.tasks
    recurring_tasks = [ task for task in tasks if task.recurring ]
    non_recurring_tasks = [ task for task in tasks if not task.recurring ]
    strresult = ''.join([ str(task) for task in non_recurring_tasks ])
    if len(recurring_tasks) > 0:
      recurring_section = TodoSection('Recurring', recurring_tasks)
      strresult += str(recurring_section)
    return strresult


class TodoSection:
  def __init__(self, header='', tasks=None, level=1):
    self.header = header
    for task in tasks: task.level = level
    self.tasks =  tasks if tasks is not None else []
    self.level = level

  def __str__(self):
    task_lines = [ f'{self.indent}{str(task)}' for task in self.tasks]
    return f'{self.indent}{self.header}:\n' + ''.join(task_lines)

  @property
  def indent(self):
    return ' ' * self.level


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

  def __str__(self):
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
