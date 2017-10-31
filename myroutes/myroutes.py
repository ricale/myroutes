import os
import json
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, jsonify
from flask_cors import CORS

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
  DATABASE=os.path.join(app.root_path, 'myroutes.db'),
  SECRET_KEY='development key',
  USERNAME='admin',
  PASSWORD='default',
  UPLOAD_FOLDER='static/pictures/'
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

def save_image_file(data, db, place):
  file_name_begin_bytes = b'filename="'
  file_name_first_pos = data.find(file_name_begin_bytes) + len(file_name_begin_bytes)
  file_name_last_pos = data.find(b'"', file_name_first_pos)
  file_name = data[file_name_first_pos:file_name_last_pos].decode('utf-8')

  content_type_begin_bytes = b'Content-Type: '
  content_type_first_pos = data.find(content_type_begin_bytes) + len(content_type_begin_bytes)
  content_type_last_pos = data.find(b'\r\n', content_type_first_pos)
  content_type = data[content_type_first_pos:content_type_last_pos].decode('utf-8')

  cur = db.execute(
    'INSERT INTO place_images (route_id, place_id, original_file_name, original_content_type) VALUES (?,?,?,?)',
    (place['route_id'], place['id'], file_name, content_type)
  )
  db.commit()

  first_pos = data.find(b'\xff\xd8')
  last_pos = data.find(b'\r\n------')
  path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], '%s-%s-%s.%s' % (place['route_id'], place['id'], cur.lastrowid, 'jpg'))
  f = open(path, 'wb')
  f.write(data[first_pos:last_pos])
  f.close()

def fetch_place_images(db, place_id):
  cur = db.execute('SELECT * FROM place_images WHERE place_id = ?', place_id)
  images = fetchall(cur)

  for image in images:
    image['url'] = url_for('static', filename = 'pictures/%s-%s-%s.jpg' % (image['route_id'], image['place_id'], image['id']))

  return images

def delete_image_file(image):
  path = os.path.join(
    app.root_path,
    app.config['UPLOAD_FOLDER'],
    '%s-%s-%s.%s' % (image['route_id'], image['place_id'], image['id'], 'jpg')
  )
  os.remove(path)


@app.route('/routes', methods=['GET'])
def routes():
  db = get_db()
  cur = db.execute('SELECT * FROM routes WHERE deleted = ? ORDER BY id DESC', (0,))
  routes = fetchall(cur)
  return jsonify(dict(
    success=True,
    data=routes,
  ))

@app.route('/routes/<route_id>', methods=['GET'])
def route(route_id):
  db = get_db()
  cur = db.execute('SELECT * FROM routes WHERE id = ?', (route_id,))
  route = fetchone(cur)
  cur = db.execute('SELECT * FROM places WHERE route_id = ?', (route_id,))
  places = fetchall(cur)

  route['places'] = places

  return jsonify(dict(
    success=True,
    data=route,
  ))

@app.route('/routes', methods=['POST'])
def create_route():
  request_data = request.get_json(silent=True)
  db = get_db()
  cur = db.execute('INSERT INTO routes (name) VALUES (?)', (request_data['name'],))
  db.commit()

  for place in request_data['places']:
    db.execute(
      'INSERT INTO places (route_id, name, latitude, longitude) VALUES (?,?,?,?)',
      (cur.lastrowid, place['name'], place['latitude'], place['longitude']))

  db.commit()

  return jsonify(dict(
    success=True,
    data=dict(id=cur.lastrowid)
  ))

@app.route('/routes/<route_id>', methods=['PUT'])
def update_route(route_id):
  request_data = request.get_json(silent=True)
  db = get_db()

  db.execute('UPDATE routes SET name = ? WHERE id = ?', (request_data['name'], route_id))

  cur = db.execute('SELECT * FROM places WHERE route_id = ?', (route_id,))
  places = fetchall(cur)

  requested_place_ids = [place['id'] for place in request_data['places'] if 'id' in place]
  for place in places:
    if place['id'] not in requested_place_ids:
      db.execute(
        'DELETE FROM places WHERE id = ?',
        (place['id'],))

  for place in request_data['places']:
    if 'id' in place:
      db.execute(
        'UPDATE places SET name = ?, latitude = ?, longitude = ? WHERE id = ?',
        (place['name'], place['latitude'], place['longitude'], place['id']))
    else:
      db.execute(
        'INSERT INTO places (route_id, name, latitude, longitude) VALUES (?,?,?,?)',
        (route_id, place['name'], place['latitude'], place['longitude']))

  db.commit()

  return jsonify(dict(
    success=True
  ))

@app.route('/routes/<route_id>', methods=['DELETE'])
def delete_route(route_id):
  db = get_db()
  db.execute(
    'UPDATE routes SET deleted = ? WHERE id = ?',
    (True, route_id))
  db.commit()

  return jsonify(dict(
    success=True
  ))




@app.route('/places/<place_id>')
def place(place_id):
  db = get_db()
  cur = db.execute('SELECT * FROM places WHERE id = ?', place_id)
  place = fetchone(cur)

  place['images'] = fetch_place_images(db, place_id)

  return jsonify(dict(
    success=True,
    data=place,
  ))

# @app.route('/places/<place_id>', methods=['PUT'])
# def update_place(place_id):
#   db = get_db()
#   cur = db.execute('SELECT * FROM places WHERE id = ?', place_id)
#   place = fetchone(cur)

#   place['images'] = fetch_place_images(db, place_id)

#   return jsonify(dict(
#     success=True,
#     data=place
#   ))

@app.route('/places/<place_id>/images', methods=['POST'])
def create_place_image(place_id):
  db = get_db()
  cur = db.execute('SELECT * FROM places WHERE id = ?', place_id)
  place = fetchone(cur)

  save_image_file(request.data, db, place)

  return jsonify(dict(
    success=True
  ))

@app.route('/place_images/<image_id>', methods=['DELETE'])
def delete_place_image(image_id):
  db = get_db()
  cur = db.execute('SELECT * FROM place_images WHERE id = ?', image_id)
  image = fetchone(cur)

  delete_image_file(image)

  cur = db.execute('DELETE FROM place_images WHERE id = ?', image_id)
  db.commit()

  return jsonify(dict(
    success=True
  ))
