"""Python translation of the R package utils."""

from utils.data import data
from utils.head import (
    RMatrix,
    checkHT,
    head,
    head_matrix,
    tail,
    tail_matrix,
)
from utils.locale import localeToCharset, osVersion, packageVersion
from utils.small import (
    URLdecode,
    URLencode,
    alarm,
    combn,
    compareVersion,
    flush_console,
    glob2rx,
    hasName,
    modifyList,
)
from utils.progress import (
    ProgressError,
    TxtProgressBar,
    WinProgressBar,
    close,
    getTxtProgressBar,
    getWinProgressBar,
    setTxtProgressBar,
    setWinProgressBar,
    txtProgressBar,
    winProgressBar,
)

__all__ = [
    "S3methods",
    "DollarNames",
    "AtNames",
    "romans",
    "ProgressError",
    "RMatrix",
    "URLdecode",
    "URLencode",
    "alarm",
    "checkHT",
    "combn",
    "compareVersion",
    "data",
    "flush_console",
    "glob2rx",
    "hasName",
    "head",
    "head_matrix",
    "localeToCharset",
    "modifyList",
    "osVersion",
    "packageVersion",
    "TxtProgressBar",
    "WinProgressBar",
    "close",
    "getTxtProgressBar",
    "getWinProgressBar",
    "setTxtProgressBar",
    "setWinProgressBar",
    "tail",
    "tail_matrix",
    "txtProgressBar",
    "winProgressBar",
    "apropos",
    "file_test",
]
from utils.roman import romans
from utils.at_names import AtNames
from utils.dollar_names import DollarNames
from utils.s3_methods import S3methods
from utils.apropos import apropos
from utils.file_test import file_test
