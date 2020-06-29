import re
import bs4
import json
import requests
from pathlib import Path
from datetime import date, datetime

from modules import log
from modules import utils
from modules import config


config = config.get_config('config')
log_path = Path(config['global']['log_path'])
logger = log.get_logger(utils.get_script_name(__file__), log_path=log_path)

class Bookmark:

  today = date.today().strftime('%Y-%m-%d')

  def __init__(self, url='', title='', tags=None, categories=''):
    self.url = url
    self.title = title
    self.created = self.today
    self.tags = tags
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
    return f'* [{self.title}]({self.url})'

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

  def update_url(self, url):
    self.history.append({ "date": self.today, "url": self.url })
    self.url = url

  def update_title(self, title):
    self.history.append({ "date": self.today, "title": self.title })
    self.title = title


class BookmarkCollection:

  def __init__(self):
    self.bookmarks = []

  def add(self, bookmark):
    self.bookmarks.append(bookmark)

  def delete(self, bookmark):
    found = self.find_by_url(bookmark.url)
    if found:
      self.bookmarks.remove(found)

  def load(self, fpath):
    suffix = Path(fpath).suffix
    if suffix == '.json':
      get_data = lambda f: json.load(f)
      ptype = 'json'
    elif suffix == '.md':
      get_data = lambda f: f.readlines()
      ptype = 'md'
    else:
      raise ValueError(f"cannot handle file with extension '{suffix}'")

    with open(fpath, encoding='utf-8') as file:
      data = get_data(file)
      bcp = BookmarkCollectionParser(ptype, self)
      self.bookmarks = bcp.parse(data)

  def import_nbff(self, fpath):
    with open(fpath, encoding='utf-8') as file:
      data = bs4.BeautifulSoup(file, 'html.parser')
    bcp = BookmarkCollectionParser('nbff', self)
    self.bookmarks = bcp.import_nbff(data)

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
      else:
        logger.debug(b.url)

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
      if value == 0:
        return [ b for b in self.bookmarks if b.last_request and not b.last_request.connected ]
      elif value == 10:
        return [ b for b in self.bookmarks if not b.last_request ]
      else:
        return [ b for b in self.bookmarks if b.last_request and b.last_request.status == value ]
    if by == 'tag':
      return [ b for b in self.bookmarks if value in b.tags ]
    if by == 'created':
      return [ b for b in self.bookmarks if value in b.created ]

  def get_urls(self, value, by):
    return [ b.url for b in self.get_bookmarks(value, by) ]

  def get_grouped_bookmarks_str(self, by):
    if by == 'status':
      values = list(set([ b.last_request.status for b in self.bookmarks if b.last_request and b.last_request.status ]))
      values.append(0)    # value 0 represents urls that failed to connect
      values.append(10)   # value 10 represents urls with unknown connection status
      get_title = lambda status: self._get_grouped_status_title_str(status)
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

  def _get_grouped_status_title_str(self, status):
    if status in requests.status_codes._codes:
      code_name = requests.status_codes._codes[status][0]
      return f'{status} ({code_name}):'
    elif status == 0:
      return 'Connection Failed:'
    elif status == 10:
      return 'Unknown:'
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


class BookmarkCollectionParser:

  title_pattern = r'^(#+)\s+(.+)$'
  # link_pattern = r'^\*\s\[(.+)\]\s*\((https?:\/\/[\w\d./?=#]+)\)\s*$'
  link_pattern = r'^\*\s\[(.+)\]\s*\((https?:\/\/.+)\)\s*$'

  def __init__(self, ftype, bc=None):
    self.ftype = ftype
    self.bc = bc if bc else BookmarkCollection()

  def parse(self, data):
    if self.ftype == 'json':
      return self._parse_json(data)
    if self.ftype == 'md':
      return self._parse_md(data)

  def _parse_json(self, data):
    for url in data:
      bookmark = Bookmark()
      bookmark.parse_json(data[url])
      self.bc.add(bookmark)
    return self.bc.bookmarks

  def _parse_md(self, data):
    cats = []
    update = (len(self.bc.bookmarks) > 0)
    if update: bkms = self.bc.bookmarks.copy()
    for line in data:
      # match bookmark line
      link_match = re.search(self.link_pattern, line)
      if link_match:
        url = link_match[2]
        title = link_match[1]
        if update:
          bu = self.bc.find_by_url(url)
          bt = self.bc.find_by_title(title)
          bookmark = bu if bu else bt
          if bookmark:
            bkms.remove(bookmark)
            if bu: bookmark.title = title
            if bt: bookmark.url = url
        if not update or not bookmark:
          bookmark = Bookmark(url, title)
          self.bc.add(bookmark)
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
    if update:
      for b in bkms:
        self.bc.delete(b)
    return self.bc.bookmarks

  def import_nbff(self, data):
    bkms = self.bc.bookmarks.copy()
    self._nbff_traverse_nodes(data.dl, 0, [], bkms)
    return self.bc.bookmarks

  def _nbff_traverse_nodes(self, node, level, cats, bkms):
    for child in node.children:
      if type(child) == bs4.element.NavigableString: continue
      if child.name == 'a':
        url = child.get('href')
        title = child.text
        unix_timestamp = child.get('add_date')
        unix_timestamp = int(unix_timestamp[:10]) if len(unix_timestamp) > 10 else int(unix_timestamp)
        created = datetime.fromtimestamp(unix_timestamp).strftime('%Y-%m-%d')
        bookmark = self.bc.find_by_url(url)
        if not bookmark: bookmark = self.bc.find_by_url_in_history(url)
        if not bookmark: bookmark = self.bc.find_by_title(title)
        if not bookmark: bookmark = self.bc.find_by_title_in_history(title)
        if bookmark:
          if not bookmark in bkms: continue
          bookmark.created = created
          bkms.remove(bookmark)
        else:
          bookmark = Bookmark(url, title)
          bookmark.created = created
          bookmark.categories = ' > '.join(cats)
          bookmark.tags = child.get('tags').split(',') if child.has_attr('tags') else [ t.replace(' ', '-').lower() for t in cats ]
          self.bc.add(bookmark)
      elif child.name == 'h3':
        cats = cats[:level]
        if len(cats) > level:
          cats[level] = child.text
        else:
          cats.append(child.text)
      elif child.name == 'dl':
        self._nbff_traverse_nodes(child, level+1, cats, bkms)
      elif child.name in ['p','dt','dd']:
        self._nbff_traverse_nodes(child, level, cats, bkms)
