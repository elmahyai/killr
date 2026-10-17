import statistics
import time
from datetime import date, datetime, timedelta, timezone
import xts
from xts import xcoredata as fn
# The timed call is fn, exercised by the package tests and this recording run.
print('index|class|descr')
