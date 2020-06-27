import re
import bs4
import json
import requests
from pathlib import Path
from datetime import date

from modules import log
from modules import utils
from modules import config


config = config.get_config('config')
log_path = Path(config['global']['log_path'])
logger = log.get_logger(utils.get_script_name(__file__), log_path=log_path)

class Bookmark:

  def __init__(self, url='', title='', tags=None, categories=''):
    self.url = url
    self.title = title
    self.tags = tags
    self.categories = categories
    self.validate = [ 'url', 'title' ]
    self.last_request = LastHttpRequest(False)
    self.history = []

  def parse_json(self, data):
    self.url = data['url']
    self.title = data['title']
    self.tags = data['tags']
    self.categories = data['categories']
    self.validate = data['validate']
    if 'lastHttpRequest' in data:
      self.last_request.parse(data['lastHttpRequest'])
    else:
      self.last_request = LastHttpRequest(False)
    self.history = data['history']

  @property
  def md(self):
    return f'* [{self.title}]({self.url})'

  @property
  def json(self):
    return {
      "url": self.url,
      "title": self.title,
      "tags": self.tags,
      "categories": self.categories,
      "validate": self.validate,
      "lastHttpRequest": self.last_request.json,
      "history": self.history
    }

  def update_url(self, url):
    today = date.today().strftime('%Y-%m-%d')
    self.history.append({ "date": today, "url": self.url })
    self.url = url


class BookmarkCollection:

  title_pattern = r'^(#+)\s+(.+)$'
  # link_pattern = r'^\*\s\[(.+)\]\s*\((https?:\/\/[\w\d./?=#]+)\)\s*$'
  link_pattern = r'^\*\s\[(.+)\]\s*\((https?:\/\/.+)\)\s*$'

  def __init__(self):
    self.bookmarks = []

  def add(self, bookmark):
    self.bookmarks.append(bookmark)

  def delete(self, bookmark):
    found = self.find_by_url(bookmark.url)
    if found:
      self.bookmarks.remove(found)

  def load_json(self, fpath):
    with open(fpath, encoding='utf-8') as file:
      data = json.load(file)
      self.parse_json(data)

  def load_md(self, fpath):
    with open(fpath, encoding='utf-8') as file:
      lines = file.readlines()
      self.parse_md(lines)

  def parse_json(self, data):
    for url in data:
      bookmark = Bookmark()
      bookmark.parse_json(data[url])
      self.add(bookmark)

  def parse_md(self, lines):
    cats = []
    bkms = self.bookmarks.copy()
    for line in lines:
      # match bookmark line
      link_match = re.search(self.link_pattern, line)
      if link_match:
        url = link_match[2]
        title = link_match[1]
        bookmark = self.find_by_url(url)
        if bookmark:
          bookmark.title = title
          bkms.remove(bookmark)
        else:
          bookmark = self.find_by_title(title)
          if bookmark:
            bookmark.url = url
            bkms.remove(bookmark)
          else:
            bookmark = Bookmark(url, title)
            self.add(bookmark)
            tags = [ t.replace(' ', '-').lower() for t in cats ]
            bookmark.tags = [ t.replace(' ', '-').lower() for t in cats ]
            bookmark.categories = ' > '.join(cats)
        continue
      # match title line
      title_match = re.search(self.title_pattern, line)
      if title_match:
        category = title_match[2]
        level = title_match[1].count('#') - 1
        cats = cats[:level]
        if len(cats) > level:
          cats[level] = category
        else:
          cats.append(category)

    # remove missing bookmarks
    for b in bkms:
      self.delete(b)

  def write_json(self, fpath):
    with open(fpath, 'w', encoding='utf8') as wf:
      json.dump(self.json, wf, indent=2, ensure_ascii=False)
      wf.write('\n')

  def write_md(self, fpath):
    with open(fpath, 'w', encoding='utf8') as wf:
      wf.write(f'{self.md}\n')

  def find_by_url(self, url):
    return next((b for b in self.bookmarks if b.url == url), None)

  def find_by_title(self, title):
    return next((b for b in self.bookmarks if b.title == title), None)

  @property
  def json(self):
    data = {}
    for b in self.bookmarks:
      data[b.url] = b.json
    return data

  @property
  def md(self):
    lines = []
    cats = []
    for bk in self.bookmarks:
      titles = bk.categories.split(' > ')
      for i, t in enumerate(titles, start=1):
        if t in cats: continue
        cats.append(t)
        lines.append(f"\n{'#' * i} {t}")
      lines.append(bk.md)
    return '\n'.join(lines)

  def validate(self):
    for b in self.bookmarks:
      try:
        r = requests.get(b.url)
        b.last_request = LastHttpRequest(True, r.status_code)

        # get redirect url
        if 'url' in b.validate and r.url != b.url:
          b.last_request.redirect = r.url

        # get title
        if 'title' in b.validate:
          html = bs4.BeautifulSoup(r.text, 'html.parser')
          t = html.title.text.strip() if html.title else ''
          if r.status_code == 200 and b.title != t:
            b.last_request.title = t

      except Exception as e:
        b.last_request = LastHttpRequest(False)
        logger.debug(f"couldn't connect to: {b.url}")
        logger.exception(e)

  def update_urls(self):
    for b in self.bookmarks:
      if b.last_request.redirect:
        b.update_url(b.last_request.redirect)

  def get_bookmarks(self, by, value):
    if by == 'status':
      if value == 0:
        return [ b for b in self.bookmarks if not b.last_request.connected ]
      else:
        return [ b for b in self.bookmarks if b.last_request.status == value ]
    if by == 'tag':
      return [ b for b in self.bookmarks if value in b.tags ]

  def get_urls(self, value, by):
    return [ b.url for b in self.get_bookmarks(value, by) ]

  def get_grouped_bookmarks_str(self, by):
    if by == 'status':
      values = list(set([ b.last_request.status for b in self.bookmarks if b.last_request.status ]))
      values.append(0)    # value 0 represnts urls that failed to connect
      get_title = lambda status: self._get_grouped_status_title_str(status)
    elif by == 'tag':
      tags = [ b.tags for b in self.bookmarks ]
      values = list(set([ tag for st in tags for tag in st ]))
      get_title = lambda tag: f'{tag}:'

    response = []
    for value in sorted(values):
      title = get_title(value)
      response.append(title)
      for b in self.get_bookmarks(by, value):
        response.append(f'  {b.url}')
    return '\n'.join(response)

  def _get_grouped_status_title_str(self, status):
    if status in requests.status_codes._codes:
      code_name = requests.status_codes._codes[status][0]
      return f'{status} ({code_name}):'
    elif status == 0:
      return 'Connection Failed:'
    else:
      return f'{status}:'


class LastHttpRequest:
  def __init__(self, connected, status=None, redirect=None, title=None):
    self.connected = connected
    self.status = status
    self.redirect = redirect
    self.title = title

  def parse(self, data):
    self.connected = data['establishedConnection'] if 'establishedConnection' in data else False
    self.status = data['statusCode'] if 'statusCode' in data else None
    self.redirect = data['redirectUrl'] if 'redirectUrl' in data else None
    self.title = data['pageTitle'] if 'pageTitle' in data else ''

  @property
  def json(self):
    data = { "establishedConnection": self.connected }
    if self.status:
      data["statusCode"] = self.status
    if self.redirect:
      data["redirectUrl"] = self.redirect
    if self.title:
      data["pageTitle"] = self.title
    return data
