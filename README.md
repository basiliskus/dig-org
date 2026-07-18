# dig-org

Command-line tools for organizing digital life: plain-text todo lists and a tagged bookmark collection.

## Tools

- **task-org** (`task-org.py`) — manages todo lists stored as [PlainTasks](https://github.com/aziz/PlainTasks)-style `.todo` files. Keeps a daily file (`today.todo`), a weekly file (`this-week.todo`), and a calendar of future tasks (`calendar.todo`); rolls pending tasks forward, re-creates recurring tasks, and archives completed ones.
- **bkm-org** (`bkm-org.py`) — maintains a bookmark collection in a JSON file. Add, tag, list, and delete URLs; validate links over HTTP; import from browser exports (Netscape bookmark format) or Instapaper; export to Markdown.

## Requirements

- Python 3
- For bkm-org: `requests`, `beautifulsoup4`, `tld`

```sh
pip install requests beautifulsoup4 tld
```

## Configuration

Both tools read `config/config.ini` (gitignored, create it first):

```ini
[global]
log_path = logs/

[task-org]
todo_path = /path/to/todos/
backup_path = ${todo_path}backup/
archive_path = ${todo_path}archive/

[bkm-org]
collection_fpath = /path/to/bookmarks.json
```

## Usage

### task-org

```sh
# Roll tasks forward to today, handle recurring tasks, archive completed ones
python task-org.py --update

# Show today's, this week's, or future tasks
python task-org.py --show today
python task-org.py --show week
python task-org.py --show calendar

# Dry run: log what would happen without touching any files
python task-org.py --update --test
```

Tasks are plain text lines like:

```
 [ ] write project readme @high
 [ ] water the plants @recurring
 [x] pay rent @done (20-06-17 21:32)
```

Supported tags: priorities (`@today`, `@critical`, `@high`, `@low`), `@recurring`, `@weekly`, and `@done` with a completion timestamp. Anything else (`@errand`, …) is kept as a regular tag. Tasks are sorted by priority when files are written.

### bkm-org

```sh
# Add a URL, optionally with comma-separated tags
python bkm-org.py --add https://example.com python,reference

# List all URLs grouped by tag, or URLs for one tag
python bkm-org.py --list tag
python bkm-org.py --list tag python

# Also groupable/filterable by: status, created (yyyy-mm-dd), domain, media
python bkm-org.py --list domain example.com

# Validate a single URL, or every bookmark in the collection
python bkm-org.py --validate https://example.com
python bkm-org.py --validate

# Combine a listing with an action: validate, tag, or delete the listed URLs
python bkm-org.py --list tag python --validate
python bkm-org.py --list domain example.com --add toread
python bkm-org.py --list status 0 --delete

# Import bookmarks (nbff = Netscape bookmark file, insta = Instapaper CSV)
python bkm-org.py --import nbff bookmarks.html
python bkm-org.py --import insta instapaper-export.csv

# Export the collection to Markdown, or rebuild the JSON from the Markdown
python bkm-org.py --sync md
python bkm-org.py --sync json

# Operate on a different collection file
python bkm-org.py -f other-bookmarks.json --list tag
```

## Project layout

- `task-org.py`, `bkm-org.py` — CLI entry points
- `todo.py` — task/todo-file model (parsing, sorting, archiving, recurrence)
- `bookmark.py` — bookmark/collection model (JSON storage, validation, imports)
- `modules/` — shared config, logging, and argument-parsing helpers
- `template.py` — starting point for new scripts
- `tasks.todo` — the project's own todo list
