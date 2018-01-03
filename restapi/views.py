import json
import copy
import os
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

def get_place_data():
  return

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
      place['images'] = PlaceImageSerializer(
        PlaceImage.objects.filter(place_id=place['id']),
        many=True
      ).data

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
    data['images'] = PlaceImageSerializer(
      PlaceImage.objects.filter(place_id=data['id']),
      many=True
    ).data
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
    instance.image.delete()
    instance.delete()

  def process_image(self, serializer):
    image_path = serializer.data['image']
    image_filename = image_path.split('/')[-1]
    image_name, image_extension = image_filename.split('.')

    absolute_path = os.path.join(settings.MEDIA_ROOT, image_filename)
    image = Image.open(absolute_path)

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
