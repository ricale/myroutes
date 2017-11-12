import os
import json
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, jsonify
from flask_cors import CORS
from PIL import Image, ExifTags

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

def get_file_extension_from_content_type(content_type):
  return ({
    'image/gif': 'gif',
    'image/png': 'png',
    'image/jpeg': 'jpeg'
  })[content_type]

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
  place_image_id = cur.lastrowid
  extension = get_file_extension_from_content_type(content_type)
  path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], '%s-%s-%s.%s' % (place['route_id'], place['id'], place_image_id, extension))
  f = open(path, 'wb')
  f.write(data[first_pos:last_pos])
  f.close()

  image = Image.open(path)
  exif = image._getexif()
  if 36867 in exif:
    taken_at = exif[36867]
  elif 306 in exif:
    taken_at = exif[306]
  else:
    taken_at = None

  if taken_at is not None:
    db.execute(
      'UPDATE place_images SET taken_at = ? WHERE id = ?', (taken_at, place_image_id)
    )
    db.commit()

  for orientation in ExifTags.TAGS.keys():
    if ExifTags.TAGS[orientation] == 'Orientation':
      break
  exif = dict(image._getexif().items())

  if exif[orientation] == 3:
    image = image.rotate(180, expand=True)
  elif exif[orientation] == 6:
    image = image.rotate(270, expand=True)
  elif exif[orientation] == 8:
    image = image.rotate(90, expand=True)

  image.save(path, extension)

  image.thumbnail((512, 512))
  path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], '%s-%s-%s-thumbnail-1.%s' % (place['route_id'], place['id'], place_image_id, extension))
  image.save(path, extension)

  image.thumbnail((128, 128))
  path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], '%s-%s-%s-thumbnail-2.%s' % (place['route_id'], place['id'], place_image_id, extension))
  image.save(path, extension)

  return place_image_id

def fetch_place_image(db, image_id):
  cur = db.execute('SELECT * FROM place_images WHERE id = ?', (image_id,))
  image = fetchone(cur)

  extension = get_file_extension_from_content_type(image['original_content_type'])
  image['url'] = url_for('static', filename = 'pictures/%s-%s-%s.%s' %
    (image['route_id'], image['place_id'], image['id'], extension))
  image['thumbnail1url'] = url_for('static', filename = 'pictures/%s-%s-%s-thumbnail-1.%s' %
    (image['route_id'], image['place_id'], image['id'], extension))
  image['thumbnail2url'] = url_for('static', filename = 'pictures/%s-%s-%s-thumbnail-2.%s' %
    (image['route_id'], image['place_id'], image['id'], extension))

  return image

def fetch_place_images(db, place_id):
  cur = db.execute('SELECT * FROM place_images WHERE place_id = ? ORDER BY taken_at', (place_id,))
  images = fetchall(cur)

  for image in images:
    extension = get_file_extension_from_content_type(image['original_content_type'])
    image['url'] = url_for('static', filename = 'pictures/%s-%s-%s.%s' %
      (image['route_id'], image['place_id'], image['id'], extension))
    image['thumbnail1url'] = url_for('static', filename = 'pictures/%s-%s-%s-thumbnail-1.%s' %
      (image['route_id'], image['place_id'], image['id'], extension))
    image['thumbnail2url'] = url_for('static', filename = 'pictures/%s-%s-%s-thumbnail-2.%s' %
      (image['route_id'], image['place_id'], image['id'], extension))

  return images

def fetch_route_images(db, route_id):
  cur = db.execute('SELECT * FROM place_images WHERE route_id = ? ORDER BY taken_at', (route_id,))
  images = fetchall(cur)

  for image in images:
    extension = get_file_extension_from_content_type(image['original_content_type'])
    image['url'] = url_for('static', filename = 'pictures/%s-%s-%s.%s' %
      (image['route_id'], image['place_id'], image['id'], extension))
    image['thumbnail1url'] = url_for('static', filename = 'pictures/%s-%s-%s-thumbnail-1.%s' %
      (image['route_id'], image['place_id'], image['id'], extension))
    image['thumbnail2url'] = url_for('static', filename = 'pictures/%s-%s-%s-thumbnail-2.%s' %
      (image['route_id'], image['place_id'], image['id'], extension))

  return images

def delete_image_file(image):
  path = os.path.join(
    app.root_path,
    app.config['UPLOAD_FOLDER'],
    '%s-%s-%s.%s' % (image['route_id'], image['place_id'], image['id'], get_file_extension_from_content_type(image['original_content_type']))
  )
  os.remove(path)

  path = os.path.join(
    app.root_path,
    app.config['UPLOAD_FOLDER'],
    '%s-%s-%s-thumbnail-1.%s' % (image['route_id'], image['place_id'], image['id'], get_file_extension_from_content_type(image['original_content_type']))
  )
  os.remove(path)

  path = os.path.join(
    app.root_path,
    app.config['UPLOAD_FOLDER'],
    '%s-%s-%s-thumbnail-2.%s' % (image['route_id'], image['place_id'], image['id'], get_file_extension_from_content_type(image['original_content_type']))
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
  cur = db.execute('SELECT * FROM places WHERE route_id = ? ORDER BY odr', (route_id,))
  places = fetchall(cur)

  route['places'] = places
  route['images'] = fetch_route_images(db, route_id)

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
      'INSERT INTO places (route_id, name, latitude, longitude, odr) VALUES (?,?,?,?,?)',
      (cur.lastrowid, place['name'], place['latitude'], place['longitude'], place['order']))

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

  cur = db.execute('SELECT * FROM places WHERE route_id = ? ORDER BY odr', (route_id,))
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
        'UPDATE places SET name = ?, latitude = ?, longitude = ?, odr = ? WHERE id = ?',
        (place['name'], place['latitude'], place['longitude'], place['order'], place['id']))
    else:
      db.execute(
        'INSERT INTO places (route_id, name, latitude, longitude, odr) VALUES (?,?,?,?,?)',
        (route_id, place['name'], place['latitude'], place['longitude']), place['order'])

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
  cur = db.execute('SELECT * FROM places WHERE id = ?', (place_id,))
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
  cur = db.execute('SELECT * FROM places WHERE id = ?', (place_id,))
  place = fetchone(cur)

  image_id = save_image_file(request.data, db, place)
  image = fetch_place_image(db, image_id)

  return jsonify(dict(
    success=True,
    data=image
  ))

@app.route('/place_images/<image_id>', methods=['DELETE'])
def delete_place_image(image_id):
  db = get_db()
  cur = db.execute('SELECT * FROM place_images WHERE id = ?', (image_id,))
  image = fetchone(cur)

  delete_image_file(image)

  cur = db.execute('DELETE FROM place_images WHERE id = ?', (image_id,))
  db.commit()

  return jsonify(dict(
    success=True
  ))
