DROP TABLE IF EXISTS routes;
CREATE TABLE routes (
  id INTEGER PRIMARY KEY autoincrement,
  name VARCHAR NOT NULL
);

DROP TABLE IF EXISTS places;
CREATE TABLE places (
  id INTEGER PRIMARY KEY autoincrement,
  route_id INTEGER NOT NULL,
  name VARCHAR NOT NULL,
  address VARCHAR,
  latitude FLOAT NOT NULL,
  longitude FLOAT NOT NULL,
  FOREIGN KEY(route_id) REFERENCES routes(id)
);

DROP TABLE IF EXISTS place_images;
CREATE TABLE place_images (
  id INTEGER PRIMARY KEY autoincrement,
  route_id INTEGER NOT NULL,
  place_id INTEGER NOT NULL,
  original_file_name VARCHAR,
  original_content_Type VARCHAR,
  FOREIGN KEY(route_id) REFERENCES routes(id),
  FOREIGN KEY(place_id) REFERENCES routes(id)
)
