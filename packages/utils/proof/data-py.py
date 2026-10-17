from utils import data
x = data(list="mtcars", package="datasets")["mtcars"]
print("|".join([str(x.nrow), format(x.columns[0][0], ".17g"), format(x.columns[0][-1], ".17g"), ",".join(x.names)]))
