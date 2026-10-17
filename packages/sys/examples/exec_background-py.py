import time
from r_sys import exec_background, exec_status
pid = exec_background("true", std_out=False, std_err=False)
time.sleep(0.05)
print(exec_status(pid, wait=True))
