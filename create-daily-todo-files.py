import os
import logging
import configparser
from pathlib import Path
from datetime import datetime, timedelta


TODO_EXTENSION = '.todo'
CONFIG_EXTENSION = '.ini'

script_name = os.path.splitext(os.path.basename(__file__))[0]

config = configparser.ConfigParser()
config.read(f'{script_name}{CONFIG_EXTENSION}')

log_fpath = Path(config['paths']['log_path']) / f'{script_name}.log'
logging.basicConfig(
  filename=log_fpath,
  format='[%(asctime)s][%(levelname)s] %(message)s',
  datefmt='%m/%d/%Y %I:%M:%S %p',
  level=logging.DEBUG
)

today = datetime.today()
yesterday = today - timedelta(days=1)

todo_path = Path(config['paths']['todo_path'])
today_fpath = todo_path / f"{today.strftime('%Y-%m-%d')}{TODO_EXTENSION}"

# Cleanup tasks
todo_files = [f for f in todo_path.iterdir() if f.suffix == TODO_EXTENSION]
for fpath in todo_files:
  # Cleanup unused todo files
  file_line_count = len(open(fpath).readlines())
  if file_line_count < 2:
    logging.info(f'removing unused todo file: {fpath}')
    fpath.unlink()

# Create today's todo file
if not today_fpath.exists():
  logging.info(f'creating file: {today_fpath}')
  with open(today_fpath, 'w') as file:
    file.write(f"Day of {today.strftime('%m/%d/%Y')}:\n")

# Create next week's todo file
future_day = today + timedelta(days=4)
week_number = future_day.isocalendar()[1] - future_day.replace(day=1).isocalendar()[1] + 1
week_fpath = todo_path / f"{future_day.strftime('%Y-%m')}-week-{week_number}{TODO_EXTENSION}"
if not week_fpath.exists():
  logging.info(f'creating file: {week_fpath}')
  start_of_week = future_day - timedelta(days=future_day.weekday())
  end_of_week = start_of_week + timedelta(days=6)
  with open(week_fpath, 'w') as file:
    file.write(f"Week of {start_of_week.strftime('%m/%d')} - {end_of_week.strftime('%m/%d')}:\n")
