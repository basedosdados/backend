from rest_framework import routers

from basedosdados_api.api import views

router = routers.DefaultRouter()
router.register(r"categories", views.CategoryViewSet, basename="category")