from django.db import models

class Route(models.Model):
  owner   = models.ForeignKey('auth.User', related_name='routes', on_delete=models.CASCADE)
  name    = models.CharField(max_length=100, blank=True, default='')
  deleted = models.BooleanField(default=False)

class Place(models.Model):
  owner     = models.ForeignKey('auth.User', related_name='places', on_delete=models.CASCADE)
  route     = models.ForeignKey('restapi.Route', related_name='places', on_delete=models.CASCADE)
  name      = models.CharField(max_length=100, blank=True, default='')
  address   = models.TextField()
  latitude  = models.DecimalField(max_digits=13, decimal_places=10)
  longitude = models.DecimalField(max_digits=13, decimal_places=10)
  odr       = models.IntegerField()

class PlaceImage(models.Model):
  owner                 = models.ForeignKey('auth.User',     related_name='place_images', on_delete=models.CASCADE)
  route                 = models.ForeignKey('restapi.Route', related_name='place_images', on_delete=models.CASCADE)
  place                 = models.ForeignKey('restapi.Place', related_name='images',       on_delete=models.CASCADE)
  original_file_name    = models.CharField(max_length=256)
  original_content_type = models.CharField(max_length=100)
  taken_at              = models.DateTimeField(auto_now_add=True)
