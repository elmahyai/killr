import time
from r_sys import exec_background, exec_status
pid = exec_background("false", std_out=False, std_err=False)
time.sleep(0.05)
print("false wait status " + str(exec_status(pid, wait=True)))
