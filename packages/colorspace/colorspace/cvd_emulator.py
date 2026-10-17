"""Color-vision-deficiency image batch tool and Shiny emulator (colorspace 2.1-4)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from colorspace.deutan import deutan
from colorspace.desaturate import desaturate
from colorspace.interpolate_cvd_transform import interpolate_cvd_transform
from colorspace.protanomaly_cvd import protanomaly_cvd
from colorspace.simulate_cvd import simulate_cvd
from colorspace.srgb import sRGB
from colorspace.tritan import tritan

_CVD_TYPES = ("deutan", "protan", "tritan", "desaturate")


def _check_image_type(path: str | os.PathLike[str]) -> dict[str, bool]:
    suffix = Path(path).suffix.lstrip(".").lower()
    return {"png": suffix == "png", "jpg": suffix in {"jpeg", "jpg"}}


def _protan(col, severity=1, linear=True):
    transform = interpolate_cvd_transform(protanomaly_cvd(), float(severity))
    return simulate_cvd(col, transform, linear=linear)


_CVD_CALLABLES = {
    "deutan": deutan,
    "protan": _protan,
    "tritan": tritan,
    "desaturate": desaturate,
}


def _read_png(path: Path) -> np.ndarray:
    from png.readPNG import readPNG

    return np.asarray(readPNG(path), dtype=np.float64)


def _write_png(path: Path, img: np.ndarray) -> None:
    from png.writePNG import writePNG

    writePNG(img, target=path)


def _read_jpeg(path: Path) -> np.ndarray:
    from PIL import Image

    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    return arr / 255.0


def _cvd_image(
    img: np.ndarray | str | os.PathLike[str],
    type: str,
    file: str | os.PathLike[str],
    severity: float = 1,
    linear: bool = True,
) -> bool:
    if isinstance(img, (str, os.PathLike)):
        img_path = Path(img)
        img_type = _check_image_type(img_path)
        if not img_type["png"] and not img_type["jpg"]:
            raise ValueError(
                f'Image "{img_path}" is neither png nor jpg/jpeg.'
            )
        img = _read_png(img_path) if img_type["png"] else _read_jpeg(img_path)

    img = np.asarray(img, dtype=np.float64)
    if type == "original":
        _write_png(Path(file), img)
        return True

    if type not in _CVD_CALLABLES:
        raise ValueError(f"unknown CVD type {type!r}")

    height, width = img.shape[0], img.shape[1]
    rgb = img[:, :, 0:3].reshape(-1, 3, order="F")
    simulated = _CVD_CALLABLES[type](
        sRGB(rgb), severity=severity, linear=linear
    )
    out_rgb = np.asarray(simulated.coords, dtype=np.float64)
    img = img.copy()
    img[:, :, 0] = out_rgb[:, 0].reshape(height, width, order="F")
    img[:, :, 1] = out_rgb[:, 1].reshape(height, width, order="F")
    img[:, :, 2] = out_rgb[:, 2].reshape(height, width, order="F")
    _write_png(Path(file), img)
    return True


def cvd_emulator(
    file: str | os.PathLike[str] | None = None,
    overwrite: bool = False,
    shiny_trace: bool = False,
) -> Any:
    """Run the CVD Shiny app, or batch-convert an image to four CVD previews."""
    if file is None:
        raise RuntimeError(
            "cvd_emulator Shiny GUI is not available in this environment"
        )

    img_path = Path(file)
    img_type = _check_image_type(img_path)
    if not img_type["png"] and not img_type["jpg"]:
        raise ValueError(
            f'Image "{img_path}" is neither png nor jpg/jpeg. Stop.'
        )

    parent = img_path.parent
    basename = img_path.name
    outfiles = [parent / f"{kind}_{basename}" for kind in _CVD_TYPES]

    if not overwrite:
        for outfile in outfiles:
            if outfile.exists():
                raise FileExistsError(
                    f'Output file "{outfile}" exists. '
                    f'Please remove the image manually or call '
                    f'cvd_emulator("{img_path}", overwrite=True)'
                )

    if img_type["png"]:
        in_img = _read_png(img_path)
    else:
        in_img = _read_jpeg(img_path)

    for kind in _CVD_TYPES:
        outfile = parent / f"{kind}_{basename}"
        print(f"Convert {kind:<15} -> {outfile}")
        _cvd_image(in_img, kind, outfile)

    return None
