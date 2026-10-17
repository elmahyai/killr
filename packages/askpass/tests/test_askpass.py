"""Checks for askpass."""

from askpass import askpass, ssh_askpass


def test_noninteractive_is_none(monkeypatch):
    monkeypatch.setattr("askpass.is_interactive", lambda: False)
    assert askpass("secret") is None
    assert ssh_askpass() is None
