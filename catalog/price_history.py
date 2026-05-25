from contextlib import contextmanager
from contextvars import ContextVar

from django.contrib.auth.models import AnonymousUser

_current_user = ContextVar("current_price_history_user", default=None)


def get_current_price_history_user():
    user = _current_user.get()
    if isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
        return None
    return user


@contextmanager
def price_history_user(user):
    token = _current_user.set(user)
    try:
        yield
    finally:
        _current_user.reset(token)
