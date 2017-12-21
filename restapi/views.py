from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response
from restapi.models import Route, Place, PlaceImage
from restapi.serializers import RouteSerializer, PlaceSerializer, PlaceImageSerializer, UserSerializer
from restapi.permissions import IsOwnerOrReadOnly
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404

def root(request):
  return render(request, 'root.html')

class RouteViewSet(viewsets.ModelViewSet):
  queryset = Route.objects.all()
  serializer_class = RouteSerializer
  permission_class = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly,)

  def perform_create(self, serializer):
    serializer.save(owner=self.request.user)

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
