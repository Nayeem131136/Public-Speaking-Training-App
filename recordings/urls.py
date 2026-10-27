from rest_framework.routers import SimpleRouter

from .views import RecordingViewSet

router = SimpleRouter()
router.register("recordings", RecordingViewSet, basename="recording")

urlpatterns = router.urls
