from django.conf.urls import url, include
from restapi import views
from restapi.views import RouteViewSet, PlaceViewSet
from rest_framework_jwt.views import obtain_jwt_token

urlpatterns = [
  url(r'^$', views.root),
  url(r'^routes/$',                RouteViewSet.as_view({'get': 'list', 'post': 'create'})),
  url(r'^routes/(?P<pk>[0-9]+)/$', RouteViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'delete': 'destroy'
  }), name='route-detail'),
  # url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
  url(r'^login/', obtain_jwt_token),
]
