from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ProductViewSet, SupplierViewSet

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"suppliers", SupplierViewSet, basename="supplier")

urlpatterns = router.urls
