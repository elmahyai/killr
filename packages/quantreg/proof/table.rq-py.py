from quantreg.latex import table_rq
try:
    table_rq(None)
except RuntimeError as error:
    print(str(error))
