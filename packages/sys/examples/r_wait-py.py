from r_sys import r_wait
print(r_wait(["--vanilla", "-q", "--slave", "-e", "quit(status=3)"], std_out=False, std_err=False))
