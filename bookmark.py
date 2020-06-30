import re
import bs4
import json
import requests
from pathlib import Path
from http.client import responses
from datetime import date, datetime

from modules import log
from modules import utils
from modules import config


config = config.get_config('config')
log_path = Path(config['global']['log_path'])
logger = log.get_logger(utils.get_script_name(__file__), log_path=log_path)

statusd = responses.copy()
statusd[0] = 'Connection Failed'
statusd[10] = 'Unknown'

date_format = '%Y-%m-%d'


class Bookmark:

  today = date.today().strftime(date_format)

  def __init__(self, url='', title='', created=None, tags=None, categories=''):
    self.url = url
    self.title = title
    self.created = created if created else self.today
    self.tags = tags if tags else []
    self.categories = categories
    self.validate = [ 'connection', 'url', 'title' ]
    self.last_request = None
    self.history = []

  def parse_json(self, data):
    self.url = data['url']
    self.title = data['title']
    self.created = data['created']
    self.tags = data['tags']
    self.categories = data['categories']
    self.validate = data['validate']
    if 'lastHttpRequest' in data:
      self.last_request = LastHttpRequest(False)
      self.last_request.parse(data['lastHttpRequest'])
    if 'history' in data:
      self.history = data['history']

  @property
  def md(self):
    title = utils.strip(self.title, ['*', '\n', '\r'])
    return f'* [{title}]({self.url})'

  @property
  def json(self):
    data = {
      "url": self.url,
      "title": self.title,
      "created": self.created,
      "tags": self.tags,
      "categories": self.categories,
      "validate": self.validate
    }
    if self.last_request:
      data["lastHttpRequest"] = self.last_request.json
    if self.history:
      data["history"] = self.history
    return data

  def verify(self):
    try:
      response = requests.get(self.url)
    except Exception as e:
      self.last_request = LastHttpRequest(False)
      logger.debug(f"couldn't connect to: {self.url}")
      logger.exception(e)
      return False

    self.last_request = LastHttpRequest(True, response.status_code)

    # get redirect url
    if 'url' in self.validate and response.url != self.url:
      self.last_request.redirect = response.url

    # get title
    if 'title' in self.validate:
      t = self.fetch_title(response)
      if self.title != t:
        self.last_request.title = t

    return True

  def update_url(self, url):
    self.history.append({ "date": self.today, "url": self.url })
    self.url = url

  def update_title(self, title):
    self.history.append({ "date": self.today, "title": self.title })
    self.title = title

  def fetch_title(self, response=None):
    if not response:
      try:
        response = requests.get(self.url)
      except:
        return ''

    html = bs4.BeautifulSoup(response.text, 'html.parser')
    if response.status_code == 200 and html.title:
      return html.title.text.strip()
    else:
      return ''

  @property
  def status(self):
    if not self.last_request:
      code = 10
    elif not self.last_request.connected:
      code = 0
    else:
      code = self.last_request.status
    return { "code": code, "name": statusd[code] }


class BookmarkCollection:

  def __init__(self):
    self.bookmarks = []

  def add(self, bookmark):
    found = self.find_by_url(bookmark.url)
    if not found:
      self.bookmarks.append(bookmark)
      return True
    return False

  def delete(self, bookmark):
    return self.delete_url(bookmark.url)

  def add_url(self, url, tags=None):
    bookmark = Bookmark(url)
    bookmark.fetch_title()
    if tags: bookmark.tags = tags
    return self.add(bookmark)

  def delete_url(self, url):
    found = self.find_by_url(url)
    if found:
      self.bookmarks.remove(found)
      return True
    return False

  def add_tags(self, url, tags):
    bookmark = self.find_by_url(url)
    if bookmark:
      for tag in tags:
        if not tag in bookmark.tags:
          bookmark.tags.append(tag)
      return True
    return False

  def delete_tag(self, url, tag):
    bookmark = self.find_by_url(url)
    if bookmark and tag in bookmark.tags:
      bookmark.tags.remove(tag)
      return True
    return False

  def load(self, fpath):
    suffix = Path(fpath).suffix
    if suffix == '.json':
      get_data = lambda f: json.load(f)
    elif suffix == '.md':
      get_data = lambda f: f.readlines()
    else:
      raise ValueError(f"cannot handle file with extension '{suffix}'")

    with open(fpath, encoding='utf-8') as file:
      data = get_data(file)
      bcp = BookmarkCollectionParser(suffix[1:], self.bookmarks)
      self.bookmarks = bcp.parse(data).bookmarks

  def import_nbff(self, fpath):
    with open(fpath, encoding='utf-8') as file:
      data = bs4.BeautifulSoup(file, 'html.parser')
    bcp = BookmarkCollectionParser('nbff', self.bookmarks)
    self.bookmarks = bcp.import_nbff(data).bookmarks

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

  def find_by_url_in_history(self, url):
    for b in self.bookmarks:
      if not b.history: continue
      for h in b.history:
        if 'url' in h and h['url'] == url:
          return b
    return None

  def find_by_title_in_history(self, title):
    for b in self.bookmarks:
      if not b.history: continue
      for h in b.history:
        if 'title' in h and h['title'] == title:
          return b
    return None

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
    for bk in sorted(self.bookmarks, key=lambda b: b.categories):
      titles = bk.categories.split(' > ')
      for i, t in enumerate(titles, start=1):
        if t in cats: continue
        cats.append(t)
        lines.append(f"\n{'#' * i} {t}")
      lines.append(bk.md)
    return '\n'.join(lines)

  def validate(self):
    for b in self.bookmarks:
      if not 'connection' in b.validate:
        b.last_request = None
        logger.debug(f'{b.url} (skip)')
        continue
      logger.debug(b.url)
      b.verify()

  def duplicate_urls(self):
    urls = [ b.url for b in self.bookmarks ]
    return '\n'.join(set([ u for u in urls if urls.count(u) > 1 ]))

  def update_urls(self):
    for b in self.bookmarks:
      if b.last_request and b.last_request.redirect:
        b.update_url(b.last_request.redirect)

  def update_titles(self):
    for b in self.bookmarks:
      if b.last_request and b.last_request.title:
        b.update_title(b.last_request.title)

  def get_bookmarks(self, by, value):
    if by == 'status':
      return [ b for b in self.bookmarks if b.status['code'] == value ]
    if by == 'tag':
      return [ b for b in self.bookmarks if value in b.tags ]
    if by == 'created':
      return [ b for b in self.bookmarks if value in b.created ]

  def get_urls(self, value, by):
    return [ b.url for b in self.get_bookmarks(value, by) ]

  def get_grouped_bookmarks_str(self, by):
    if by == 'status':
      values = list(set([ b.status['code'] for b in self.bookmarks ]))
      get_title = lambda code: f"{code} ({statusd[code]}):"
    elif by == 'tag':
      tags = [ b.tags for b in self.bookmarks ]
      values = list(set([ tag for st in tags for tag in st ]))
      get_title = lambda tag: f'{tag}:'
    elif by == 'created':
      values = list(set([ b.created for b in self.bookmarks ]))
      get_title = lambda created: f'{created}:'

    response = []
    for value in sorted(values):
      title = get_title(value)
      response.append(title)
      for b in self.get_bookmarks(by, value):
        response.append(f'  {b.url}')
    return '\n'.join(response)


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


class BookmarkCollectionParser(BookmarkCollection):

  title_pattern = r'^(#+)\s+(.+)$'
  # link_pattern = r'^\*\s\[(.+)\]\s*\((https?:\/\/[\w\d./?=#]+)\)\s*$'
  link_pattern = r'^\*\s\[(.*)\]\s*\((https?:\/\/.+)\)\s*$'

  def __init__(self, ftype, bookmarks=None):
    self.ftype = ftype
    self.bookmarks = bookmarks if bookmarks else []

  def parse(self, data):
    if self.ftype == 'json':
      return self._parse_json(data)
    if self.ftype == 'md':
      return self._parse_md(data)

  def _parse_json(self, data):
    for url in data:
      bookmark = Bookmark()
      bookmark.parse_json(data[url])
      if not self.add(bookmark):
        logger.debug(f'not able to add: {bookmark.url}')
    return self

  def _parse_md(self, data):
    cats = []
    update = (len(self.bookmarks) > 0)
    if update: bkms = self.bookmarks.copy()
    for line in data:
      # match bookmark line
      link_match = re.search(self.link_pattern, line)
      if link_match:
        url = link_match[2]
        title = link_match[1]
        if update:
          bu = self.find_by_url(url)
          bt = self.find_by_title(title)
          bookmark = bu if bu else bt
          if bookmark:
            bkms.remove(bookmark)
            if bu: bookmark.title = title
            if bt: bookmark.url = url
        if not update or not bookmark:
          bookmark = Bookmark(url, title)
          if not self.add(bookmark):
            logger.debug(f'not able to add: {bookmark.url}')
        if cats:
          bookmark.tags = [ utils.get_tag_from_category(t) for t in cats ]
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
    if update:
      for b in bkms:
        if not self.delete(b):
          logger.debug(f'not able to delete: {b.url}')
    return self

  def import_nbff(self, data):
    self._nbff_traverse_nodes(data.dl, 0, [])
    return self

  def _nbff_traverse_nodes(self, node, level, cats):
    for child in node.children:
      if type(child) == bs4.element.NavigableString: continue
      if child.name == 'a':
        url = child.get('href')
        title = child.text
        created = utils.get_date_from_unix_timestamp(child.get('add_date')).strftime(date_format)
        bookmark = self.find_by_url(url)
        if not bookmark: bookmark = self.find_by_url_in_history(url)
        if not bookmark: bookmark = self.find_by_title(title)
        if not bookmark: bookmark = self.find_by_title_in_history(title)
        if bookmark:
          if datetime.strptime(created, date_format) < datetime.strptime(bookmark.created, date_format):
            bookmark.created = created
        else:
          bookmark = Bookmark(url, title, created)
          bookmark.categories = ' > '.join(cats)
          bookmark.tags = child.get('tags').split(',') if child.has_attr('tags') else [ t.replace(' ', '-').lower() for t in cats ]
          if not self.add(bookmark):
            logger.debug(f'not able to add: {bookmark.url}')
      elif child.name == 'h3':
        cats = cats[:level]
        if len(cats) > level:
          cats[level] = child.text
        else:
          cats.append(child.text)
      elif child.name == 'dl':
        self._nbff_traverse_nodes(child, level+1, cats)
      elif child.name in ['p','dt','dd']:
        self._nbff_traverse_nodes(child, level, cats)
