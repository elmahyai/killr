suppressPackageStartupMessages(library(tools))

one <- function() {
  o <- Rd2txt_options()
  paste0(o$width, " ", o$minIndent, " ", o$extraIndent, " ", o$sectionIndent, " ", o$sectionExtra, " ",
         o$showURLs, " ", o$code_quote, " ", o$underline_titles, " ", o$itemBullet, o$enumFormat(3), "\n")
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
