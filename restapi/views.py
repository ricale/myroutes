import json
import copy
import os
import string
from pytz import timezone
from datetime import datetime
from PIL import Image, ExifTags
from django.contrib.auth.models import User
from django.shortcuts import render
from django.http import QueryDict
from django.conf import settings
from rest_framework import permissions, viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.parsers import FileUploadParser
from restapi.models import Route, Place, PlaceImage
from restapi.serializers import RouteSerializer, PlaceSerializer, PlaceImageSerializer, UserSerializer
from restapi.permissions import IsOwnerOrReadOnly

def get_thumbnail1_path(filename):
  return '{0}{1}{2}'.format(settings.MEDIA_ROOT, '/thumbnail1/', filename)

def get_thumbnail2_path(filename):
  return '{0}{1}{2}'.format(settings.MEDIA_ROOT, '/thumbnail2/', filename)

def get_place_image_data(place_id):
  data = PlaceImageSerializer(
    PlaceImage.objects.filter(place_id=place_id).order_by('taken_at'),
    many=True
  ).data

  for d in data:
    thumbnail1_url = '{0}{1}'.format(settings.MEDIA_URL, 'thumbnail1/')
    d['thumbnail1'] = d['image'].replace(settings.MEDIA_URL, thumbnail1_url)
    thumbnail2_url = '{0}{1}'.format(settings.MEDIA_URL, 'thumbnail2/')
    d['thumbnail2'] = d['image'].replace(settings.MEDIA_URL, thumbnail2_url)

  return data

class RouteViewSet(viewsets.ModelViewSet):
  queryset = Route.objects.all()
  serializer_class = RouteSerializer
  permission_class = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly,)

  def perform_create(self, serializer):
    serializer.save(owner=self.request.user)

  def get_data_and_related(self, serializer):
    data = copy.deepcopy(serializer.data)
    data['places'] = PlaceSerializer(
      Place.objects.filter(route_id=serializer.data['id']).order_by('odr'),
      many=True
    ).data

    for place in data['places']:
      place['images'] = get_place_image_data(place['id'])

    return data

  def perform_create_places(self, serializer):
    route = Route.objects.get(id=serializer.data['id'])

    place_data = self.request.data.get('places')
    if place_data:
      for place in place_data:
        qdict = QueryDict('', mutable=True)
        qdict.update(place)
        place_serializer = PlaceSerializer(data=qdict)
        place_serializer.is_valid(raise_exception=True)
        place_serializer.save(owner=self.request.user, route=route)

  def perform_update_places(self, serializer):
    route = Route.objects.get(id=serializer.data['id'])
    place_records = Place.objects.filter(route_id=serializer.data['id'])
    place_data = self.request.data.get('places')
    place_data_ids = [d['id'] for d in place_data if hasattr(d, 'id')]

    for record in place_records:
      if record.id not in place_data_ids:
        record.delete()

    for data in place_data:
      qdict = QueryDict('', mutable=True)
      qdict.update(data)

      try:
        place = [p for p in place_records if p.id == data['id']][0]
        place_serializer = PlaceSerializer(place[0], data=qdict)
      except:
        place_serializer = PlaceSerializer(data=qdict)

      place_serializer.is_valid(raise_exception=True)
      place_serializer.save(owner=self.request.user, route=route)

  def retrieve(self, request, *args, **kwargs):
    instance = self.get_object()
    serializer = self.get_serializer(instance)
    response_data = self.get_data_and_related(serializer)
    return Response(response_data)

  def create(self, request, *args, **kwargs):
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    self.perform_create(serializer)
    self.perform_create_places(serializer)
    headers = self.get_success_headers(serializer.data)
    return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

  def update(self, request, *args, **kwargs):
    instance = self.get_object()
    serializer = self.get_serializer(instance, data=request.data)
    serializer.is_valid(raise_exception=True)
    self.perform_update(serializer)
    self.perform_update_places(serializer)
    return Response(serializer.data)

class PlaceViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
  queryset = Place.objects.all()
  serializer_class = PlaceSerializer
  permission_class = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly,)

  def get_data_and_related(self, serializer):
    data = copy.deepcopy(serializer.data)
    data['images'] = get_place_image_data(data['id'])
    return data

  def retrieve(self, request, *args, **kwargs):
    instance = self.get_object()
    serializer = self.get_serializer(instance)
    response_data = self.get_data_and_related(serializer)
    return Response(response_data)

class PlaceImageViewSet(viewsets.ModelViewSet):
  queryset = PlaceImage.objects.all()
  serializer_class = PlaceImageSerializer
  permission_class = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly,)
  parser_classes = (FileUploadParser,)

  def perform_create(self, serializer, place):
    serializer.save(owner=self.request.user, route=place.route, place=place)

  def perform_destroy(self, instance):
    thumbnail1_path = get_thumbnail1_path(instance.image)
    os.remove(thumbnail1_path)
    thumbnail2_path = get_thumbnail2_path(instance.image)
    os.remove(thumbnail2_path)
    instance.image.delete()
    instance.delete()

  def process_image(self, serializer):
    image_path = serializer.data['image']
    image_filename = image_path.split('/')[-1]
    image_name, image_extension = image_filename.split('.')

    absolute_path = os.path.join(settings.MEDIA_ROOT, image_filename)
    image = Image.open(absolute_path)
    exif = image._getexif()
    if 36867 in exif:
      taken_at = exif[36867]
    elif 306 in exif:
      taken_at = exif[306]
    else:
      taken_at = None

    if taken_at is not None:
      place_image = PlaceImage.objects.get(id=serializer.data['id'])
      taken_datetime = datetime.strptime(taken_at, '%Y:%m:%d %H:%M:%S')
      if taken_datetime.strftime('%z') == '':
        tz = timezone('Asia/Seoul')
        taken_datetime = tz.localize(taken_datetime)
      place_image.taken_at = taken_datetime
      place_image.save()

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

    image.save(absolute_path)

    image.thumbnail((512, 512))
    thumbnail1_absolute_path = os.path.join(settings.MEDIA_ROOT, 'thumbnail1/{0}.{1}'.format(image_name, image_extension))
    image.save(thumbnail1_absolute_path)

    image.thumbnail((128, 128))
    thumbnail2_absolute_path = os.path.join(settings.MEDIA_ROOT, 'thumbnail2/{0}.{1}'.format(image_name, image_extension))
    image.save(thumbnail2_absolute_path)

  def create(self, request, *args, **kwargs):
    qdict = QueryDict('', mutable=True)
    qdict.update(dict(image=request.data['file']))

    serializer = self.get_serializer(data=qdict)
    serializer.is_valid(raise_exception=True)
    place = Place.objects.get(id=kwargs['place_id'])
    self.perform_create(serializer, place)
    self.process_image(serializer)
    return Response(serializer.data)

class UserViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = User.objects.all()
  serializer_class = UserSerializer
