# Sort drops missing values

R's `sort` removes `NA` and `NaN` when `na.last` is left at its default. A NumPy sort keeps those missing values at the end, so a port that sorts and then searches has to drop them first or the result is longer than R's.
