from tools.base_aliases_db import base_aliases_db

db = base_aliases_db(verbose=False, ncpus=1)
print(len(db))
print(",".join(db))
print(",".join(db["stats"]["acf.Rd"]))
