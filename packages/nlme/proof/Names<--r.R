.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

enc_chr <- function(x) {
  if (is.null(x)) return(-1)
  c(length(x), unlist(lapply(x, function(s) c(utf8ToInt(s), 0))))
}
enc_list <- function(lst) unlist(lapply(lst, enc_chr))
safe <- function(expr) tryCatch(expr, error = function(e) -2)

one <- function() {
  data(Pixel)
  rs <- reStruct(list(Dog = ~day, Side = ~1), data = Pixel)
  pd <- pdMat(~day, data = Pixel)
  pd_perm <- pd
  Names(pd_perm) <- c("day", "(Intercept)")
  initialized <- pdMat(matrix(c(2, 0.5, 0.5, 1), 2),
                       nam = c("a", "b"), pdClass = "pdLogChol")
  Names(initialized) <- c("b", "a")
  pd_suffix <- pd
  Names(pd_suffix) <- c("day.(Intercept)", "(Intercept)")
  pd_null <- pd
  Names(pd_null) <- NULL
  rs_perm <- rs
  Names(rs_perm) <- list("(Intercept)", c("day", "(Intercept)"))
  c(
    enc_chr(Names(pd_perm)),
    enc_chr(Names(pd_suffix)),
    enc_chr(Names(pd_null)),
    enc_chr(Names(initialized)),
    enc_list(Names(rs_perm)),
    safe({
      pd_bad <- pd
      Names(pd_bad) <- c("foo", "(Intercept)")
      enc_chr(Names(pd_bad))
    }),
    safe({
      pd_len <- pd
      Names(pd_len) <- c("a")
      enc_chr(Names(pd_len))
    }),
    safe({
      rs_len <- rs
      Names(rs_len) <- list("a")
      enc_list(Names(rs_len))
    })
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
