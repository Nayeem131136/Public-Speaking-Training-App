"""Which filler words are active for a user."""
from django.db.models import Q

from services.fillers import DEFAULT_FILLER_WORDS

from .models import FillerWord


def get_active_filler_words(user, language="en"):
    """Global filler words plus the user's own words, for one language."""
    words = set()
    if not FillerWord.objects.filter(owner__isnull=True).exists() and language == "en":
        words.update(DEFAULT_FILLER_WORDS)

    owner_filter = Q(owner__isnull=True)
    if user is not None:
        owner_filter |= Q(owner=user)
    saved = FillerWord.objects.filter(is_active=True, language=language).filter(owner_filter)
    words.update(saved.values_list("word", flat=True))
    return sorted(words)
