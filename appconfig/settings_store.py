"""Read the settings: database values on top of the defaults."""
from .defaults import DEFAULTS
from .models import AppSetting


def get_all_settings():
    values = dict(DEFAULTS)
    for row in AppSetting.objects.filter(key__in=DEFAULTS.keys()):
        values[row.key] = row.value
    return values


def get_setting(key):
    return get_all_settings()[key]
