import askpass as ask
ask.options["rlib_interactive"] = False
print("NULL" if ask.askpass("x") is None else "SET")
