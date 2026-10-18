library(labelled)
x <- labelled_spss(c(1, NA, 9), na_values=9)
one <- function() is_regular_na(x)
value <- one(); z <- numeric(20)
for (i in seq_along(z)) { a <- Sys.time(); one(); z[i] <- as.numeric(Sys.time()-a)*1000 }
cat(jsonlite::toJSON(list(value=value, median_ms=median(z)), auto_unbox=TRUE))
