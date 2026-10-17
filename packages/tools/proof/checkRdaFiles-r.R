suppressPackageStartupMessages(library(tools))

one <- function() {
  path <- "/home/ahmed/killr_projects/killr/packages/tools/proof/tiny.rda"
  res <- checkRdaFiles(c(path, "/tmp/no-such-tools-file.rda"))
  show <- function(x) ifelse(is.na(x), "NA", as.character(x))
  paste0(
    show(res$size[1]), " ", show(res$ASCII[1]), " ", show(res$compress[1]), " ", show(res$version[1]), "\n",
    show(res$size[2]), " ", show(res$ASCII[2]), " ", show(res$compress[2]), " ", show(res$version[2]), "\n"
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
