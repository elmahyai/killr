"""Defunct pillar helpers.

``is_vector_s3()`` and ``expect_known_display()`` stop. The message is the
one lifecycle prints for package pillar, including the wrap at the session width.
"""

from __future__ import annotations

from typing import Any

from lifecycle import LifecycleError

from pillar._layout import defunct_message


def is_vector_s3(x: Any = None) -> None:
    """Defunct. Use ``vctrs::vec_is()``."""

    raise LifecycleError(
        defunct_message("1.7.0", "pillar::is_vector_s3()", "vctrs::vec_is()")
    )


def expect_known_display(*_args: Any, **_kwargs: Any) -> None:
    """Defunct. Use ``testthat::expect_snapshot()``."""

    raise LifecycleError(
        defunct_message(
            "1.7.0",
            "pillar::expect_known_display()",
            "testthat::expect_snapshot()",
        )
    )
