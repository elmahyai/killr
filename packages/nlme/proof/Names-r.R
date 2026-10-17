.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

enc_chr <- function(x) {
  if (is.null(x)) return(-1)
  c(length(x), unlist(lapply(x, function(s) c(utf8ToInt(s), 0))))
}
enc_list <- function(lst) unlist(lapply(lst, enc_chr))

one <- function() {
  data(Pixel)
  rs <- reStruct(list(Dog = ~day, Side = ~1), data = Pixel)
  pd <- pdMat(~day, data = Pixel)
  c(
    enc_list(Names(rs)),
    enc_chr(Names(pd)),
    enc_chr(Names(~day, data = Pixel)),
    enc_chr(Names(~1)),
    enc_chr(Names(~day)),
    enc_list(Names(structure(list(~day, ~1), class = "listForm"), data = Pixel))
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
