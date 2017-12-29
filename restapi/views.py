import json
import copy
from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response
from restapi.models import Route, Place, PlaceImage
from restapi.serializers import RouteSerializer, PlaceSerializer, PlaceImageSerializer, UserSerializer
from restapi.permissions import IsOwnerOrReadOnly
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404
from django.http import QueryDict

def root(request):
  return render(request, 'root.html')

class RouteViewSet(viewsets.ModelViewSet):
  queryset = Route.objects.all()
  serializer_class = RouteSerializer
  permission_class = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly,)

  def perform_create(self, serializer):
    serializer.save(owner=self.request.user)

  def retrieve(self, request, *args, **kwargs):
    route = self.get_object()
    serializer = self.get_serializer(route)

    route_data = copy.deepcopy(serializer.data)
    route_data['places'] = PlaceSerializer(
      Place.objects.filter(route_id=route.id).order_by('odr'),
      many=True
    ).data

    return Response(route_data)

  def create(self, request, *args, **kwargs):
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    self.perform_create(serializer)

    route = Route.objects.get(id=serializer.data['id'])

    place_data = request.data.get('places')

    if place_data:
      for place in place_data:
        place['route_id'] = serializer.data['id']
        qdict = QueryDict('', mutable=True)
        qdict.update(place)
        place_serializer = PlaceSerializer(data=qdict)
        place_serializer.is_valid(raise_exception=True)
        place_serializer.save(owner=self.request.user, route=route)

    headers = self.get_success_headers(serializer.data)
    return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

  def update(self, request, *args, **kwargs):
    instance = self.get_object()
    serializer = self.get_serializer(instance, data=request.data)
    serializer.is_valid(raise_exception=True)
    self.perform_update(serializer)

    route = Route.objects.get(id=serializer.data['id'])
    place_records = Place.objects.filter(route_id=serializer.data['id'])
    place_data = request.data.get('places')
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

    return Response(serializer.data)

class PlaceViewSet(viewsets.ModelViewSet):
  queryset = Place.objects.all()
  serializer_class = PlaceSerializer
  permission_class = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly,)

  def perform_create(self, serializer):
    route_id = self.request.data['route_id']
    route = get_object_or_404(Route, id=route_id)
    serializer.save(owner=self.request.user, route=route)

class PlaceImageViewSet(viewsets.ModelViewSet):
  queryset = PlaceImage.objects.all()
  serializer_class = PlaceImageSerializer
  permission_class = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly,)

class UserViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = User.objects.all()
  serializer_class = UserSerializer
