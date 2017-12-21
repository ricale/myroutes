from django.conf.urls import url, include
from restapi import views
from rest_framework.routers import SimpleRouter
from rest_framework_jwt.views import obtain_jwt_token

router = SimpleRouter()
router.register(r'routes', views.RouteViewSet)
router.register(r'places', views.PlaceViewSet)
router.register(r'place_images', views.PlaceImageViewSet)
router.register(r'users', views.UserViewSet)

urlpatterns = [
  url(r'^', include(router.urls)),
  url(r'^$', views.root),
  # url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
  url(r'^api-token-auth/', obtain_jwt_token),
]
