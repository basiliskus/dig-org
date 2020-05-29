from pathlib import Path
from datetime import datetime, timedelta

from modules import log
from modules import utils
from modules import config


TODO_EXTENSION = '.todo'

script_name = utils.get_script_name(__file__)
config = config.get_config(script_name)
log_path = Path(config['paths']['log_path'])
logger = log.get_logger(script_name, log_path=log_path)

def main():
  todo_path = Path(config['paths']['todo_path'])
  today = datetime.today()
  yesterday = today - timedelta(days=1)

  # Cleanup tasks
  todo_files = [f for f in todo_path.iterdir() if f.suffix == TODO_EXTENSION]
  cleanup(todo_files)

  # Create today's todo file
  today_fpath = todo_path / f"{today.strftime('%Y-%m-%d')}{TODO_EXTENSION}"
  day_file_content = f"Day of {today.strftime('%m/%d/%Y')}:\n"
  create_file(today_fpath, day_file_content)

  # Create next week's todo file
  future_day = today + timedelta(days=4)
  start_of_week = future_day - timedelta(days=future_day.weekday())
  end_of_week = start_of_week + timedelta(days=6)
  week_number = future_day.isocalendar()[1] - future_day.replace(day=1).isocalendar()[1] + 1
  week_fpath = todo_path / f"{future_day.strftime('%Y-%m')}-week-{week_number}{TODO_EXTENSION}"
  week_file_content = f"Week of {start_of_week.strftime('%m/%d')} - {end_of_week.strftime('%m/%d')}:\n"
  create_file(week_fpath, week_file_content)

def create_file(fpath, content):
  if not fpath.exists():
    logger.info(f'creating file: {fpath}')
    with open(fpath, 'w') as file:
      file.write(content)

def cleanup(files):
  for fpath in files:
    # Cleanup unused todo files
    file_line_count = len(open(fpath).readlines())
    if file_line_count < 2:
      logger.info(f'removing unused file: {fpath}')
      fpath.unlink()


if __name__ == "__main__":
  main()
