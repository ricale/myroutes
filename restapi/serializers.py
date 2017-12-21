from rest_framework import serializers
from restapi.models import Route, Place, PlaceImage
from django.contrib.auth.models import User

class RouteSerializer(serializers.HyperlinkedModelSerializer):
  owner = serializers.ReadOnlyField(source='owner.username')

  places       = serializers.HyperlinkedRelatedField(many=True, view_name='place-detail', read_only=True)
  place_images = serializers.HyperlinkedRelatedField(many=True, view_name='place-image-detail', read_only=True)

  class Meta:
    model = Route
    fields = ('url', 'id', 'owner', 'places', 'place_images', 'name', 'deleted')

class PlaceSerializer(serializers.HyperlinkedModelSerializer):
  owner = serializers.ReadOnlyField(source='owner.username')
  route = serializers.ReadOnlyField(source='route.id')

  place_images = serializers.HyperlinkedRelatedField(many=True, view_name='place-detail', read_only=True)

  class Meta:
    model = Place
    fields = ('url', 'id', 'owner', 'route',
              'name', 'address', 'latitude', 'longitude', 'odr', 'place_images')

class PlaceImageSerializer(serializers.HyperlinkedModelSerializer):
  owner = serializers.ReadOnlyField(source='owner.username')
  route = serializers.ReadOnlyField(source='route.id')
  place = serializers.ReadOnlyField(source='place.id')

  class Meta:
    model = PlaceImage
    fields = ('url', 'id', 'owner', 'route', 'place',
              'original_file_name', 'original_content_type', 'taken_at')

class UserSerializer(serializers.HyperlinkedModelSerializer):
  routes       = serializers.HyperlinkedRelatedField(many=True, view_name='route-detail', read_only=True)
  places       = serializers.HyperlinkedRelatedField(many=True, view_name='place-detail', read_only=True)
  place_images = serializers.HyperlinkedRelatedField(many=True, view_name='place-image-detail', read_only=True)

  class Meta:
    model = User
    fields = ('url', 'id', 'username', 'routes', 'places', 'place_images')
