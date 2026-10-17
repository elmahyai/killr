from askpass import ssh_askpass
print("NULL" if ssh_askpass() is None else "SET")
