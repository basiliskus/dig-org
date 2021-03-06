import re
import csv
import json
import uuid
import logging
from http.client import responses
from datetime import datetime
from collections import defaultdict

import cgi
import bs4
import requests
from tld import get_fld, get_tld

from modules import utils


logger = logging.getLogger('bkm-org')
date_format = '%Y-%m-%d'
datetime_format = '%Y-%m-%d %H:%M:%S'


class Bookmark:

  statusd = responses.copy()
  statusd[0] = 'Connection Failed'
  statusd[10] = 'Unknown'

  def __init__(self, url='', title='', created=None, tags=None, categories=''):
    self.id = uuid.uuid4()
    self.url = url
    self.title = title
    self.mtype = 'unknown'
    self.created = created if created else datetime.now()
    self.tags = tags if tags else []
    self.categories = categories
    self.vtypes = ['connection', 'url', 'title']
    self.lrequest = None
    self.history = []

  def parse_json(self, data):
    self.id = uuid.UUID(data['id'])
    self.url = data['url']
    self.title = data['title']
    if 'mediaType' in data:
      self.mtype = data['mediaType']
    self.created = datetime.strptime(data['created'], datetime_format)
    self.tags = data['tags']
    self.categories = data['categories']
    if 'validation' in data:
      self.vtypes = data['validation']['types']
      if 'lastHttpRequest' in data['validation']:
        self.lrequest = LastHttpRequest(False)
        self.lrequest.parse(data['validation']['lastHttpRequest'])
    if 'history' in data:
      self.history = data['history']

  @property
  def md(self):
    strip_chars = ['\n', '\r']
    escape_chars = ['*', '_']
    title = utils.escape(utils.strip(self.title, strip_chars), escape_chars) if self.title else self.url
    return f'* [{title}]({self.url})'

  @property
  def json(self):
    data = {}
    data["id"] = str(self.id)
    data["url"] = self.url
    data["title"] = self.title
    data["mediaType"] = self.mtype
    data["created"] = self.created.strftime(datetime_format)
    data["tags"] = self.tags
    data["categories"] = self.categories
    data["validation"] = {"types": self.vtypes}
    if self.lrequest:
      data["validation"]["lastHttpRequest"] = self.lrequest.json
    if self.history:
      data["history"] = self.history
    return data

  def verify(self):
    try:
      response = requests.get(self.url, timeout=(2, 10))
    except Exception as e:
      self.lrequest = LastHttpRequest(False)
      logger.error(f"error connecting to: {self.url}")
      logger.debug(e)
      return False

    self.lrequest = LastHttpRequest(True, response.status_code)

    # get redirect url
    if 'url' in self.vtypes and response.url != self.url:
      self.lrequest.redirect = response.url

    ctype = response.headers.get('content-type', None)
    if ctype:
      if not self.mtype:
        self.mtype = cgi.parse_header(ctype)[0]
    else:
      logger.debug(f"not able to get content-type for '{self.url}'")

    if self.mtype != 'text/html': return True

    # get title
    if 'title' in self.vtypes:
      t = self.fetch_title(response)
      if self.title != t:
        self.lrequest.title = t

    return True

  def update_url(self, url):
    self.history.append({"date": datetime.now().strftime(datetime_format), "url": self.url})
    self.url = url

  def update_title(self, title):
    self.history.append({"date": datetime.now().strftime(datetime_format), "title": self.title})
    self.title = title

  def fetch_title(self, response=None):
    if not response:
      try:
        response = requests.get(self.url, timeout=(2, 10))
      except Exception as e:
        logger.debug(f"not able to get response from '{self.url}' to fecth title")
        logger.debug(e)
        return ''

    html = bs4.BeautifulSoup(response.text, 'html.parser')
    if response.status_code == 200 and html.title:
      return html.title.text.strip()
    else:
      return ''

  def add_tags(self, tags):
    at_least_one_tag_added = False
    for tag in tags:
      if tag not in self.tags:
        self.tags.append(tag)
        at_least_one_tag_added = True
    return at_least_one_tag_added

  def delete_tag(self, tag):
    if tag in self.tags:
      self.tags.remove(tag)
      return True
    return False

  @property
  def status(self):
    if not self.lrequest:
      code = 10
    elif not self.lrequest.connected:
      code = 0
    else:
      code = self.lrequest.status
    status_name = self.statusd[code] if code in self.statusd else 'Unknown Status Code'
    return {"code": code, "name": status_name}


class BookmarkCollection:

  ignore_titles = ['Untitled', '']

  def __init__(self, fpath=None, name='', description='', catalog='default'):
    self.name = name
    self.description = description
    self.catalog = catalog
    self.bookmarks = []
    self.fpath = fpath
    if fpath and fpath.exists():
      self.load(fpath)

  def add(self, bookmark):
    found = self.find_by_url(bookmark.url)
    if not found:
      self.bookmarks.append(bookmark)
      return True
    return False

  def delete(self, bookmark):
    return self.delete_url(bookmark.url)

  def add_url(self, url, title=None, tags=None):
    bookmark = Bookmark(url)
    if title:
      bookmark.title = title
    else:
      bookmark.fetch_title()
    if tags:
      bookmark.tags = tags
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
      return bookmark.add_tags(tags)
    return False

  def delete_tag(self, url, tag):
    bookmark = self.find_by_url(url)
    if bookmark:
      return bookmark.delete_tag(tag)
    return False

  def load(self, fpath):
    self.fpath = fpath

    if fpath.suffix == '.json':
      get_data = lambda f: json.load(f)
    elif fpath.suffix == '.md':
      get_data = lambda f: f.readlines()
    else:
      raise ValueError(f"cannot handle file with extension '{fpath.suffix}'")

    with open(fpath, encoding='utf-8') as file:
      data = get_data(file)
      bcp = BookmarkCollectionParser(fpath.suffix[1:], self.bookmarks)
      parsedbc = bcp.parse(data)
      self.name = parsedbc.name
      self.description = parsedbc.description
      self.catalog = parsedbc.catalog
      self.bookmarks = parsedbc.bookmarks

  def import_md(self):
    self.load(self.fpath.with_suffix('.md'))

  def import_nbff(self, fpath):
    with open(fpath, encoding='utf-8') as file:
      data = bs4.BeautifulSoup(file, 'html.parser')
    bcp = BookmarkCollectionParser('nbff', self.bookmarks)
    parsedbc = bcp.import_nbff(data)
    self.name = parsedbc.name
    self.description = parsedbc.description
    self.catalog = parsedbc.catalog
    self.bookmarks = parsedbc.bookmarks

  def import_instapaper(self, fpath):
    with open(fpath, encoding='utf-8') as csv_file:
      reader = csv.DictReader(csv_file)
      bcp = BookmarkCollectionParser('insta', self.bookmarks)
      parsedbc = bcp.import_instapaper(reader)
      self.name = parsedbc.name
      self.description = parsedbc.description
      self.catalog = parsedbc.catalog
      self.bookmarks = parsedbc.bookmarks

  def write(self, fpath=None):
    if not fpath and self.fpath:
      fpath = self.fpath
    elif not self.fpath:
      raise ValueError("no file path to write to defined")

    if fpath.suffix == '.json':
      self.write_json(fpath)
    elif fpath.suffix == '.md':
      self.write_md(fpath)
    else:
      raise ValueError(f"cannot handle file with extension '{fpath.suffix}'")

  def write_json(self, fpath=None):
    if not fpath and self.fpath:
      fpath = self.fpath.with_suffix('.json')
    elif not self.fpath:
      raise ValueError("no file path to write to defined")

    with open(fpath, 'w', encoding='utf8') as wf:
      json.dump(self.json, wf, indent=2, ensure_ascii=False)
      wf.write('\n')

  def write_md(self, fpath=None):
    if not fpath and self.fpath:
      fpath = self.fpath.with_suffix('.md')
    elif not self.fpath:
      raise ValueError("no file path to write to defined")

    with open(fpath, 'w', encoding='utf8') as wf:
      wf.write(f'{self.md}\n')

  def find(self, url, title=None):
    bookmark = self.find_by_url(url)
    if not bookmark: bookmark = self.find_by_url_in_history(url)
    if not title: return bookmark
    if not bookmark: bookmark = self.find_by_title(title)
    if not bookmark: bookmark = self.find_by_title_in_history(title)
    return bookmark

  def find_update(self, url, title):
    bookmark = self.find_by_url(url)
    bookmark = bookmark if bookmark else self.find_by_url_in_history(url)
    if bookmark:
      bookmark.title = title
    return bookmark

  def find_by_url(self, url):
    return next((b for b in self.bookmarks if b.url == url), None)

  def find_by_title(self, title):
    if title in self.ignore_titles: return None
    return next((b for b in self.bookmarks if b.title == title), None)

  def find_by_url_in_history(self, url):
    for b in self.bookmarks:
      if not b.history: continue
      for h in b.history:
        if 'url' in h and h['url'] == url:
          return b
    return None

  def find_by_title_in_history(self, title):
    if title in self.ignore_titles: return None
    for b in self.bookmarks:
      if not b.history: continue
      for h in b.history:
        if 'title' in h and h['title'] == title:
          return b
    return None

  @property
  def json(self):
    data = {
        "name": self.name,
        "description": self.description,
        "catalog": self.catalog,
        "bookmarks": []
    }
    for b in sorted(self.bookmarks, key=lambda b: b.created, reverse=True):
      data["bookmarks"].append(b.json)
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
      if 'connection' not in b.vtypes:
        b.lrequest = None
        logger.info(f'{b.url} (skip)')
        continue
      logger.info(b.url)
      b.verify()

  def sync_urls(self):
    for b in self.bookmarks:
      if b.lrequest and b.lrequest.redirect:
        b.update_url(b.lrequest.redirect)
        b.lrequest.redirect = None

  def sync_titles(self):
    for b in self.bookmarks:
      if b.lrequest and b.lrequest.title:
        b.update_title(b.lrequest.title)
        b.lrequest.title = None

  def get_bookmarks(self, by, value):
    if by == 'status':
      return [b for b in self.bookmarks if b.status['code'] == int(value)]
    if by == 'tag':
      return [b for b in self.bookmarks if value in b.tags]
    if by == 'created':
      return [b for b in self.bookmarks if value in b.created.strftime(date_format)]
    if by == 'domain':
      return [b for b in self.bookmarks if get_fld(b.url) == value]
    if by == 'media':
      return [b for b in self.bookmarks if value in b.mtype]

  def get_urls(self, value, by):
    return [b.url for b in self.get_bookmarks(value, by)]

  def get_grouped_urls(self, by):
    result = defaultdict(list)
    if by == 'status':
      for b in self.bookmarks:
        result[f"{b.status['code']} ({b.status['name']})"].append(b.url)
    elif by == 'tag':
      for b in self.bookmarks:
        for tag in b.tags:
          result[tag].append(b.url)
    elif by == 'created':
      for b in self.bookmarks:
        result[b.created.strftime(date_format)].append(b.url)
    elif by == 'domain':
      for b in self.bookmarks:
        result[get_fld(b.url)].append(b.url)
    elif by == 'media':
      for b in self.bookmarks:
        result[b.mtype].append(b.url)
    return result


class BookmarkCollectionCatalog:

  ignore_files = ['template.json', 'test.json']

  def __init__(self, name, path):
    self.name = name
    self.path = path
    self.collections = []
    self.load()

  def load(self):
    fpaths = [f for f in self.path.glob('*.json') if f.name not in self.ignore_files]
    for cpath in fpaths:
      bc = BookmarkCollection(cpath)
      if bc.catalog == self.name:
        self.collections.append(bc)


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
    data = {"establishedConnection": self.connected}
    if self.status:
      data["statusCode"] = self.status
    if self.redirect:
      data["redirectUrl"] = self.redirect
    if self.title:
      data["pageTitle"] = self.title
    return data


class BookmarkCollectionParser(BookmarkCollection):

  title_pattern = r'^(#+)\s+(.+)$'
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
    self.name = data['name']
    self.description = data['description']
    self.catalog = data['catalog']
    for bjson in data['bookmarks']:
      bookmark = Bookmark()
      bookmark.parse_json(bjson)
      if not self.add(bookmark):
        logger.debug(f'not able to add: {bookmark.url}')
    return self

  def _parse_md(self, data):
    cats = []
    bkms = self.bookmarks.copy()

    for line in data:

      # match bookmark line
      link_match = re.search(self.link_pattern, line)
      if link_match:
        url = link_match[2]
        title = link_match[1]
        bookmark = self.find_update(url, title)
        if bookmark:
          if bookmark in bkms:
            bkms.remove(bookmark)
          else:
            logger.debug(f'duplicated: {bookmark.url}')
        else:
          bookmark = Bookmark(url, title)
          if not self.add(bookmark):
            logger.debug(f'not able to add: {bookmark.url}')
            continue
        if cats:
          bookmark.categories = ' > '.join(cats)
          bookmark.add_tags([utils.get_tag_from_category(t) for t in cats])
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
      if not self.delete(b):
        logger.debug(f'not able to delete: {b.url}')
      else:
        logger.debug(f'deleted: {b.url}')

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
        created = utils.get_date_from_unix_timestamp(child.get('add_date'))
        bookmark = self.find(url, title)
        if bookmark:
          if created < bookmark.created:
            bookmark.created = created
        else:
          bookmark = Bookmark(url, title, created)
          bookmark.categories = utils.get_category_hierarchy_str(cats)
          bookmark.tags = child.get('tags').split(',') if child.has_attr('tags') else [utils.get_tag_from_category(c) for c in cats]
          if not self.add(bookmark):
            logger.debug(f'not able to add: {bookmark.url}')
      elif child.name == 'h3':
        cats = cats[:level]
        if len(cats) > level:
          cats[level] = child.text
        else:
          cats.append(child.text)
      elif child.name == 'dl':
        self._nbff_traverse_nodes(child, level + 1, cats)
      elif child.name in ['p', 'dt', 'dd']:
        self._nbff_traverse_nodes(child, level, cats)

  def import_instapaper(self, data):
    for row in data:
      bookmark = Bookmark(row['URL'], row['Title'])
      bookmark.created = utils.get_date_from_unix_timestamp(row['Timestamp'])
      bookmark.categories = row['Folder']
      bookmark.tags.append(utils.get_tag_from_category(row['Folder']))
      if not self.add(bookmark):
        logger.debug(f'not able to add: {bookmark.url}')
    return self
