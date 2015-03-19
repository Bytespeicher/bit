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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return 'Main page'
    elif request.method == 'POST':
        return 'New url'

@app.route('/<link_id>')
def short_link(link_id):
    url = util.lookup_url(link_id)
    if url == None:
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
    app.run(host='localhost', port=9002, debug=True)
