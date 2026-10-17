suppressPackageStartupMessages(library(tools))

one <- function() {
  g <- Adobe_glyphs
  raw <- charToRaw(paste(g$adobe, g$unicode, sep="=", collapse="|"))
  paste0("GLYPH ", length(g$adobe), " ", md5sum(bytes=raw), " ", g$adobe[1], " ", g$unicode[1], " ", g$adobe[length(g$adobe)], " ", g$unicode[length(g$unicode)], "\n")
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
