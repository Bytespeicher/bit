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


app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, config.DATABASE_PATH),
    DEBUG=True,
))


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
    if wish is not None:
        exists = lookup_url(wish)
    if exists is None:
        pass
    pass


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return 'Main page'
    elif request.method == 'POST':
        return 'New url'

@app.route('/<link_id>')
def short_link(link_id):
    url = lookup_url(link_id)
    if url is None:
        abort(404)
    else:
        return redirect(url)

@app.route('/<link_url>+')
def link_info(link_url):
    return json.dumps({'Link:': link_url})

@app.route('/api/v1/short', methods=['POST'])
def api_v1_short():
    return json.dumps(request)

@app.route('/api/v1/long', methods=['POST'])
def api_v1_long():
    return json.dumps(request)

if __name__ == "__main__":
    app.run(host='localhost', port=9002)
