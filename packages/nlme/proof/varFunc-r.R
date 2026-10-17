.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

one <- function() {
  vp <- varPower(0.35, form = ~x)
  err <- tryCatch({
    varFunc(1)
    0
  }, error = function(e) 1)
  c(
    as.numeric(is.null(varFunc(NULL))),
    as.numeric(identical(varFunc(vp), vp)),
    as.numeric(identical(class(varFunc(~x)), c("varFixed", "varFunc"))),
    as.numeric(identical(class(varFunc("~x")), c("varFixed", "varFunc"))),
    length(all.vars(formula(varFunc(~x)))),
    err
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
