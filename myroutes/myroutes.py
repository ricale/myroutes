import os
import sys
import json
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, jsonify
from flask_cors import CORS
from PIL import Image, ExifTags
import flask_login

from google.oauth2 import id_token
from google.auth.transport import requests

app = Flask(__name__)
app.secret_key = 'ea3e59e14bd7809c65d6d1f6fa4d67eb59fa8045c24efddc';
app.config.from_object(__name__)

app.config.update(dict(
  DATABASE=os.path.join(app.root_path, 'myroutes.db'),
  SECRET_KEY='ea3e59e14bd7809c65d6d1f6fa4d67eb59fa8045c24efddc',
  USERNAME='admin',
  PASSWORD='default',
  UPLOAD_FOLDER='static/pictures/',
  CORS_SUPPORTS_CREDENTIALS=True
))
app.config.from_envvar('MYROUTES_SETTINGS', silent=True)

cors = CORS(app, resources={r"*": {"origins": "*"}})

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

class User(flask_login.UserMixin):
  pass



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
  fetched = cur.fetchone()
  if fetched is None:
    return None
  return dict(zip(columns, fetched))



@login_manager.user_loader
def user_loader(google_id):
  db = get_db()
  cur = db.execute('SELECT * FROM users WHERE google_id = ?', (google_id,))
  user = fetchone(cur)

  user = User()
  user.id        = google_id
  user.google_id = google_id
  # user.email     = user['email']
  # user.name      = user['name']
  return user

# @login_manager.request_loader
# def request_loader(request):
#   pass

@login_manager.unauthorized_handler
def unauthorized_handler():
  return jsonify(dict(
    success=False,
    message='Login first.'
  )), 401



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

  user_id = flask_login.current_user.id
  cur = db.execute(
    'INSERT INTO place_images (route_id, place_id, original_file_name, original_content_type, user_id) VALUES (?,?,?,?,?)',
    (place['route_id'], place['id'], file_name, content_type, user_id)
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

  if orientation in exif:
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
@flask_login.login_required
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

  for place in places:
    place['images'] = fetch_place_images(db, place['id'])

  route['places'] = places

  route['images'] = fetch_route_images(db, route_id)

  return jsonify(dict(
    success=True,
    data=route,
  ))

@app.route('/routes', methods=['POST'])
@flask_login.login_required
def create_route():
  request_data = request.get_json(silent=True)
  user_id = flask_login.current_user.id
  db = get_db()
  cur = db.execute('INSERT INTO routes (name, user_id) VALUES (?, ?)', (request_data['name'], user_id))
  db.commit()

  for place in request_data['places']:
    db.execute(
      'INSERT INTO places (route_id, name, latitude, longitude, odr, user_id) VALUES (?,?,?,?,?,?)',
      (cur.lastrowid, place['name'], place['latitude'], place['longitude'], place['order'], user_id))

  db.commit()

  return jsonify(dict(
    success=True,
    data=dict(id=cur.lastrowid)
  ))

@app.route('/routes/<route_id>', methods=['PUT'])
@flask_login.login_required
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
        (place['name'], place['latitude'], place['longitude'], place['order'], place['id'])
      )
    else:
      db.execute(
        'INSERT INTO places (route_id, name, latitude, longitude, odr) VALUES (?,?,?,?,?)',
        (route_id, place['name'], place['latitude'], place['longitude'], place['order'])
      )

  db.commit()

  return jsonify(dict(
    success=True
  ))

@app.route('/routes/<route_id>', methods=['DELETE'])
@flask_login.login_required
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

@app.route('/places/<place_id>/images', methods=['POST'])
@flask_login.login_required
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
@flask_login.login_required
def delete_place_image(image_id):
  db = get_db()
  cur = db.execute('SELECT * FROM place_images WHERE id = ?', (image_id,))
  image = fetchone(cur)

  try:
    delete_image_file(image)
  except:
    print("Unexpected error:", sys.exc_info()[0])
    pass

  cur = db.execute('DELETE FROM place_images WHERE id = ?', (image_id,))
  db.commit()

  return jsonify(dict(
    success=True
  ))




@app.route('/login', methods=['POST'])
def login():
  request_data = request.get_json(silent=True)
  token     = request_data['token']
  google_id = request_data['google_id']
  email     = request_data['email']
  name      = request_data['name']

  CLIENT_ID = '891848771699-7vgvpu31bp20tqfmtk66b72ukusqfumt.apps.googleusercontent.com'

  try:
    idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
    if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
      raise ValueError('Wrong issuer.')
    # idinfo['sub'] is google_id
  except ValueError:
    return jsonify(dict(
      success=False
    ))

  db = get_db()
  cur = db.execute('SELECT * FROM users WHERE google_id = ?', (google_id,))
  record = fetchone(cur)

  if record is None:
    cur = db.execute(
      'INSERT INTO users (google_id, email, name) VALUES (?,?,?)',
      (google_id, email, name)
    )
    db.commit()

  user = User()
  user.id        = google_id
  user.google_id = google_id
  user.email     = email
  user.name      = name

  flask_login.login_user(user)

  return jsonify(dict(
    success=True,
    data=dict(
      google_id=google_id,
      email=email,
      name=name,
    )
  ))

@app.route('/logout')
def logout():
  flask_login.logout_user()
  return jsonify(dict(
    success=True
  ))

@app.route('/users')
def users():
  db = get_db()
  cur = db.execute('SELECT * FROM users ORDER BY id DESC')
  users = fetchall(cur)
  return jsonify(dict(
    success=True,
    data=users,
  ))
