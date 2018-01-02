from django.db import models

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

class PlaceImage(models.Model):
  owner    = models.ForeignKey('auth.User',     related_name='place_images', on_delete=models.CASCADE)
  route    = models.ForeignKey('restapi.Route', related_name='place_images', on_delete=models.CASCADE)
  place    = models.ForeignKey('restapi.Place', related_name='place_images', on_delete=models.CASCADE)
  image    = models.ImageField(null=True)
  taken_at = models.DateTimeField(auto_now_add=True)
