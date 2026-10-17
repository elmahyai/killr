from r_sys import exec_internal
out = exec_internal("printf", ["%s", "hello"])
print(str(out["status"]) + " " + out["stdout"].decode())
