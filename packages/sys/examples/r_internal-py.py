from r_sys import r_internal
out = r_internal(["--vanilla", "-q", "--slave", "-e", "cat(6*7)"])
print(out["stdout"].decode())
