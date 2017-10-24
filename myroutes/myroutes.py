import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, jsonify
from flask_cors import CORS

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
  DATABASE=os.path.join(app.root_path, 'myroutes.db'),
  SECRET_KEY='development key',
  USERNAME='admin',
  PASSWORD='default'
))
app.config.from_envvar('MYROUTES_SETTINGS', silent=True)

cors = CORS(app, resources={r"*": {"origins": "*"}})

def connect_db():
  rv = sqlite3.connect(app.config['DATABASE'])
  rv.row_factory = sqlite3.Row
  return rv

def get_db():
  if not hasattr(g, 'sqlite_db'):
    g.sqlite_db = connect_db()
  return g.sqlite_db

def init_db():
  db = get_db()
  with app.open_resource('schema.sql', mode='r') as f:
    db.cursor().executescript(f.read())
  db.commit()

@app.cli.command('initdb')
def initdb_command():
  init_db()
  print('Initialized the database.')

@app.teardown_appcontext
def close_db(error):
  if hasattr(g, 'sqlite_db'):
    g.sqlite_db.close()

def fetchall(cur):
  columns = [column[0] for column in cur.description]
  results = []
  for row in cur.fetchall():
    results.append(dict(zip(columns, row)))
  return results

def fetchone(cur):
  columns = [column[0] for column in cur.description]
  return dict(zip(columns, cur.fetchone()))




@app.route('/routes', methods=['GET'])
def routes():
  db = get_db()
  cur = db.execute('SELECT * FROM routes ORDER BY id DESC')
  routes = fetchall(cur)
  return jsonify(dict(
    result=True,
    data=routes,
  ))

@app.route('/routes/<route_id>', methods=['GET'])
def route(route_id):
  db = get_db()
  cur = db.execute('SELECT * FROM routes WHERE id = ?', route_id)
  route = fetchone(cur)
  return jsonify(dict(
    result=True,
    data=route,
  ))

@app.route('/routes', methods=['POST'])
def create_route():
  request_data = request.get_json(silent=True)
  db = get_db()
  cur = db.execute('INSERT INTO routes (name) VALUES (?)', (request_data['name'],))
  db.commit()
  return jsonify(dict(
    result=True
  ))

@app.route('/routes/<route_id>', methods=['PUT'])
def update_route(route_id):
  request_data = request.get_json(silent=True)
  db = get_db()
  cur = db.execute('UPDATE routes SET name=? WHERE id=?', (request_data['name'], route_id))
  db.commit()
  return jsonify(dict(
    success=True
  ))
