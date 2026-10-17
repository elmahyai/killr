"""Write hexadecimal color descriptions."""

from colorspace._cspace_convert import as_srgb_coords, hex_from_srgb
import sys


def writehex(x, file=""):
    """Write one hexadecimal color per line and return the file name."""
    values = hex_from_srgb(as_srgb_coords(x))
    text = "\n".join("" if value is None else value for value in values) + "\n"
    if file == "":
        sys.stdout.write(text)
    else:
        with open(file, "w", encoding="utf-8") as output:
            output.write(text)
    return file
