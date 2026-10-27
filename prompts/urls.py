from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, PromptViewSet

router = SimpleRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("prompts", PromptViewSet, basename="prompt")

urlpatterns = router.urls
