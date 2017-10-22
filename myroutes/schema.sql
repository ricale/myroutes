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
  latitude FLOAT NOT NULL,
  longitude FLOAT NOT NULL
);
