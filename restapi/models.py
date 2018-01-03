from django.db import models

import uuid

class Route(models.Model):
  owner   = models.ForeignKey('auth.User', related_name='routes', on_delete=models.CASCADE)
  name    = models.CharField(max_length=100, blank=True, default='')
  deleted = models.BooleanField(default=False)

class Place(models.Model):
  owner     = models.ForeignKey('auth.User', related_name='places', on_delete=models.CASCADE)
  route     = models.ForeignKey('restapi.Route', related_name='places', on_delete=models.CASCADE)
  name      = models.CharField(max_length=100, blank=True, default='')
  address   = models.TextField(null=True)
  latitude  = models.DecimalField(max_digits=18, decimal_places=15)
  longitude = models.DecimalField(max_digits=18, decimal_places=15)
  odr       = models.IntegerField()


def get_image_path(instance, filename):
  return '{0}.{1}'.format(instance.id, filename.split(".")[-1])

class PlaceImage(models.Model):
  id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  owner    = models.ForeignKey('auth.User',     related_name='place_images', on_delete=models.CASCADE)
  route    = models.ForeignKey('restapi.Route', related_name='place_images', on_delete=models.CASCADE)
  place    = models.ForeignKey('restapi.Place', related_name='place_images', on_delete=models.CASCADE)
  image    = models.ImageField(null=True, upload_to=get_image_path)
  taken_at = models.DateTimeField(auto_now_add=True)
