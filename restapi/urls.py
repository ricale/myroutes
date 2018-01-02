from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from rest_framework_jwt.views import obtain_jwt_token
from restapi import views
from restapi.views import RouteViewSet, PlaceViewSet, PlaceImageViewSet

urlpatterns = [
  url(r'^$', views.root),
  url(r'^routes/$',                RouteViewSet.as_view({'get': 'list', 'post': 'create'})),
  url(r'^routes/(?P<pk>[0-9]+)/$', RouteViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'delete': 'destroy'
  }), name='route-detail'),

  url(r'^places/(?P<pk>[0-9]+)/$', PlaceViewSet.as_view({'get': 'retrieve'})),
  url(r'^places/(?P<place_id>[0-9]+)/images/$', PlaceImageViewSet.as_view({'post': 'create'})),

  url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
  url(r'^login/', obtain_jwt_token),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
