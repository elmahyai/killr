from r_sys import exec_status, r_background
pid = r_background(["--vanilla", "-q", "--slave", "-e", "quit(status=0)"], std_out=False, std_err=False)
print(exec_status(pid, wait=True))
