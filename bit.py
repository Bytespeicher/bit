#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json

from flask import Flask
from flask import request
from flask import g
from flask import redirect
from flask import abort
from flask import render_template
from flask import flash

import os
import config
import sqlite3
import time

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, config.DATABASE_PATH),
    DEBUG=True,
))


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
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema/v1.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


def lookup_url(link_id):
    db = get_db()
    cur = db.execute('SELECT url FROM urls WHERE key = ?', (link_id,))
    link = cur.fetchall()
    if len(link) is not 1:
        return None
    else:
        return link


def save_url(url, wish=None):
    exists = None
    db = get_db()
    if wish is not None:
        exists = lookup_url(wish)
    else:
        cur = db.execute('SELECT key FROM urls WHERE url = ?', (url,))
        key_exists = cur.fetchone()

    if exists is None:
        key = wish
    elif key_exists is not None:
        cur = db.execute('SELECT key FROM urls ORDER BY key LIMIT 1')
        last_key = cur.fetchone()
        if not last_key:
            key = base62_encode(0)
        else:
            key = base62_encode(base62_decode(last_key) + 1)
    else:
        key = key_exists

    db.execute('INSERT INTO urls (key, url) VALUES (?, ?)', (key, url))
    db.commit()


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
        return redirect(url)


@app.route('/save', methods=['POST'])
def save_link():
    if not len(request['url']):
        flash('No URL supplied')
        return redirect('/')

    key = save_url(request['url'])
    return redirect('/' + key + '+')


@app.route('/<link_id>+')
def link_info(link_id):
    link_url = lookup_url(link_id)
    if link_url is None:
        abort(404)

    db = get_db()
    link_stats = db.execute('SELECT time FROM stats WHERE link_id = ?',
                            (link_id,))

    return json.dumps({'Link:': link_url, 'Stats:': link_stats})


@app.route('/api/v1/short', methods=['POST'])
def api_v1_short():
    if not request.form['key']:
        return json.dumps({'error': 'Authorization required'}), 401

    # TODO: url validation
    if not request.form['url']:
        return json.dumps({'error': 'URL required'}), 400

    short_link = save_url(request.form['url'], request.form['wish'])

    return short_link


@app.route('/api/v1/long', methods=['POST'])
def api_v1_long():
    return json.dumps(request)


if __name__ == "__main__":
    app.run(host='localhost', port=9002)
