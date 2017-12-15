from rest_framework import generics, permissions, renderers, viewsets
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from restapi.models import Route, Place, PlaceImage
from restapi.serializers import RouteSerializer, PlaceSerializer, PlaceImageSerializer, UserSerializer
from restapi.permissions import IsOwnerOrReadOnly
from django.contrib.auth.models import User
from django.shortcuts import render

def root(request):
  return render(request, 'root.html')

class RouteViewSet(viewsets.ModelViewSet):
  queryset = Route.objects.all()
  serializer_class = RouteSerializer
  permission_class = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly,)

class PlaceViewSet(viewsets.ModelViewSet):
  queryset = Place.objects.all()
  serializer_class = PlaceSerializer
  permission_class = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly,)

class PlaceImageViewSet(viewsets.ModelViewSet):
  queryset = PlaceImage.objects.all()
  serializer_class = PlaceImageSerializer
  permission_class = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly,)

class UserViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = User.objects.all()
  serializer_class = UserSerializer
