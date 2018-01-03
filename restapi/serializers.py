from rest_framework import serializers
from restapi.models import Route, Place, PlaceImage
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
  routes       = serializers.PrimaryKeyRelatedField(many=True, queryset=Route.objects.all(), allow_null=True)
  places       = serializers.PrimaryKeyRelatedField(many=True, queryset=Place.objects.all(), allow_null=True)
  place_images = serializers.PrimaryKeyRelatedField(many=True, queryset=PlaceImage.objects.all(), allow_null=True)

  class Meta:
    model = User
    fields = ('id', 'username', 'routes', 'places', 'place_images')

class RouteSerializer(serializers.ModelSerializer):
  owner = serializers.ReadOnlyField(source='owner.username')

  # places       = serializers.PrimaryKeyRelatedField(many=True, queryset=Place.objects.all(), allow_null=True)
  # place_images = serializers.PrimaryKeyRelatedField(many=True, queryset=PlaceImage.objects.all(), allow_null=True)

  class Meta:
    model = Route
    fields = ('id', 'owner', 'name', 'deleted')

class PlaceSerializer(serializers.ModelSerializer):
  owner = serializers.ReadOnlyField(source='owner.username')
  route = serializers.ReadOnlyField(source='route.id')

  # place_images = serializers.PrimaryKeyRelatedField(many=True, queryset=PlaceImage.objects.all(), allow_null=True)

  class Meta:
    model = Place
    fields = ('id', 'owner', 'route', 'route_id',
              'name', 'address', 'latitude', 'longitude', 'odr')

class PlaceImageSerializer(serializers.ModelSerializer):
  id    = serializers.UUIDField(read_only=True)
  owner = serializers.ReadOnlyField(source='owner.username')
  route = serializers.ReadOnlyField(source='route.id')
  place = serializers.ReadOnlyField(source='place.id')

  image = serializers.ImageField(use_url=True)

  class Meta:
    model = PlaceImage
    fields = ('id', 'owner', 'route', 'place',
              'image', 'taken_at')
