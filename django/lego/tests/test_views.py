"""Unit tests for the views module."""

from views import handle_cleanup, handle_present


def handle_present_when_user_has_permission():
    handle_present()
    assert False


def handle_present_when_user_has_no_permission():
    handle_present()
    assert False


def handle_cleanup_when_user_has_permission():
    handle_cleanup()
    assert False


def handle_cleanup_when_user_has_no_permission():
    handle_cleanup()
    assert False