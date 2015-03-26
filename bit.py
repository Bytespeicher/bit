#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json
import click
import os
import config
import sqlite3
import time

from flask import Flask
from flask import request
from flask import g
from flask import redirect
from flask import abort
from flask import render_template
from flask import flash
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, config.DATABASE_PATH),
    DEBUG=True,
))


class JSONException(HTTPException):
    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.response = response

        if status_code is not None:
            self.code = status_code
        else:
            self.code = 400

    def get_body(self, environ):
        return json.dumps({
            "error": self.message,
            "code": self.code
        })

    def get_headers(self, environ):
        return [('Content-Type', 'application/json')]


ALPHABET = "23456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"


def base62_encode(num, alphabet=ALPHABET):
    """Encode a number in Base X

    `num`: The number to encode
    `alphabet`: The alphabet to use for encoding
    """
    if (num == 0):
        return alphabet[0]
    arr = []
    base = len(alphabet)
    while num:
        rem = num % base
        num = num // base
        arr.append(alphabet[rem])
    arr.reverse()
    return ''.join(arr)


def base62_decode(string, alphabet=ALPHABET):
    """Decode a Base X encoded string into the number

    Arguments:
    - `string`: The encoded string
    - `alphabet`: The alphabet to use for encoding
    """
    base = len(alphabet)
    strlen = len(string)
    num = 0

    idx = 0
    for char in string:
        power = (strlen - (idx + 1))
        num += alphabet.index(char) * (base ** power)
        idx += 1

    return num


def connect_db():
    """Connects to the specific database."""
    def make_dicts(cursor, row):
        return dict((cursor.description[idx][0], value)
                    for idx, value in enumerate(row))

    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = make_dicts
    return rv


def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema/v1.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


def lookup_url(link_id):
    db = get_db()
    cur = db.execute('SELECT url FROM urls WHERE key = ? LIMIT 1', (link_id,))
    link = cur.fetchone()
    if link is None:
        return None
    else:
        return link['url']


def lookup_stats(link_id):
    db = get_db()
    cur = db.execute('SELECT time FROM stats WHERE link_id = ?', (link_id,))
    link_stats = [x['time'] for x in cur.fetchall()]

    return link_stats


def save_url(url, wish=None, api_key=None):
    db = get_db()

    if wish is not None:
        exists = lookup_url(wish)
        if exists is not None:
            return wish
        else:
            if api_key is not None:
                db.execute('INSERT INTO urls (key, url, api_key) VALUES (?, ?, ?)',
                           (wish, url, api_key))
            else:
                db.execute('INSERT INTO urls (key, url) VALUES (?, ?)', (wish, url))

            db.commit()
            return wish
    else:
        try:
            cur = db.execute('SELECT key FROM urls WHERE url = ?', (url,))
            key_exists = cur.fetchone()[0]
            if key_exists is not None:
                return key_exists
        except TypeError:
            key_exists = None

    cur = db.execute('SELECT key FROM urls ORDER BY key LIMIT 1')
    last_key = cur.fetchone()

    if not last_key or last_key == '':
        key = base62_encode(8)
    else:
        key = base62_encode(base62_decode(last_key) + 1)

    if api_key is not None:
        db.execute('INSERT INTO urls (key, url, api_key) VALUES (?, ?, ?)',
                   (key, url, api_key))
    else:
        db.execute('INSERT INTO urls (key, url) VALUES (?, ?)', (key, url))

    db.commit()
    return key


@app.cli.command('initdb')
@click.option('--upgrade', default='no', help='Only upgrade to a newer version')
def initdb_command(upgrade):
    if upgrade == 'yes':
        print('Not implemented')
        return
    else:
        """Creates the database tables."""
        init_db()
        print('Initialized the database.')


@app.cli.command('addkey')
@click.option('--key', help='The API key to add')
@click.option('--limit', default=10000, help='Maximum requests per day')
def add_api_key(key, limit):
    """Adds an API key for authorization."""
    if key is None or len(key) is not 32:
        print('Keys must be exactly 32 characters long!')
        return

    if limit == 0:
        print('INFO: Limit set to 0 - setting no limit.')

    if limit < 0:
        print('INFO: Limit is less than 0, disabling account')

    db = get_db()
    db.execute('INSERT OR REPLACE INTO api (key, dlimit) VALUES (?, ?)',
               (key, limit))
    db.commit()

    print('Key "%s" added to the database.' % key)


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.route('/<link_id>')
def short_link(link_id):
    url = lookup_url(link_id)
    if url is None:
        abort(404)
    else:
        db = get_db()
        db.execute('INSERT INTO stats (link_id, time) VALUES(?, ?)',
                   (link_id, int(time.time()),))
        db.commit()
        return redirect(url, code=301)


@app.route('/save', methods=['POST'])
def save_link():
    if not len(request.form['url']):
        flash('No URL supplied')
        return redirect('/')

    key = save_url(request.form['url'])

    if key is None:
        abort(500)

    return redirect('/' + key + '+')


@app.route('/<link_id>+')
def link_info(link_id):
    link_url = lookup_url(link_id)
    if link_url is None:
        abort(404)

    link_stats = lookup_stats(link_id)

    return json.dumps({'Link:': link_url, 'Stats:': link_stats})


@app.route('/api/v1/short', methods=['POST'])
def api_v1_short():
    if not request.json:
        raise JSONException(message="No data supplied", status_code=400)

    # TODO: api key validation
    if 'key' not in request.json:
        raise JSONException(message="No valid API key supplied",
                            status_code=401)

    # TODO: url validation
    if 'url' not in request.json:
        raise JSONException(message="No URL supplied", status_code=400)

    if 'wish' not in request.json:
        wish = None
    else:
        wish = request.json['wish']

    try:
        short_link = save_url(request.json['url'], wish, api_key=request.json['key'])
        return json.dumps({
            "url_long": request.json['url'],
            "url_short": short_link,
            "wish": wish
        })
    except Exception:
        return JSONException(message="Internal server error", status_code=500)


@app.route('/api/v1/long', methods=['POST'])
def api_v1_long():
    if not request.json:
        raise JSONException(message="No data supplied", status_code=400)

    # TODO: api key validation
    if 'key' not in request.json:
        raise JSONException(message="No valid API key supplied",
                            status_code=401)

    if 'id' not in request.json:
        raise JSONException(message="No URL id supplied", status_code=400)

    try:
        long_link = lookup_url(request.json['id'])
        if long_link is None:
            JSONException(message="Link information not found", status_code=404)

        if 'statistics' in request.json and request.json['statistics'] is True:
            statistics = lookup_stats(request.json['id'])
        else:
            statistics = []

        return json.dumps({
            "url_short": request.json['id'],
            "url_long": long_link,
            "statistics": statistics
        })
    except Exception:
        return JSONException(message="Internal server error", status_code=500)

if __name__ == "__main__":
    app.run(host='localhost', port=9002)
