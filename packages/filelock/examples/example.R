
mylockfile <- tempfile()
lck <- lock(mylockfile)
print(lck)
lock(mylockfile, timeout = 0)
lock(mylockfile, timeout = 5000)
lock(mylockfile, timeout = Inf)
invisible(unlock(lck))
