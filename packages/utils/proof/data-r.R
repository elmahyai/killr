e <- new.env()
data(list = "mtcars", package = "datasets", envir = e)
x <- e$mtcars
cat(paste(nrow(x), sprintf("%.17g", x$mpg[1]), sprintf("%.17g", x$mpg[nrow(x)]), paste(names(x), collapse = ","), sep = "|"), "\n")
