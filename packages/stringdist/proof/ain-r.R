suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

one <- function() {
  c(
    as.numeric(ain("leia", c("uhura", "leela"), maxDist = 5)),
    as.numeric(ain("leia", c("uhura", "leela"), maxDist = 1)),
    as.numeric(ain(c("leia", "uhura"), c("ripley", "leela", "scully", "trinity"), maxDist = 2)),
    as.numeric(ain("leia", c("uhura", "leela"), maxDist = Inf)),
    as.numeric(ain("leia", c("uhura", "leela"), maxDist = 2)),
    as.numeric(ain("MARTHA", c("MATHRA", "MARHTA"), method = "jw", maxDist = 0.2)),
    as.numeric(ain("abc", c("cba", "abc"), method = "osa", maxDist = 2)),
    as.numeric(ain("ab", "ba", method = "hamming", maxDist = 2)),
    as.numeric(ain("Mot\u00f6rhead", "Motorhead", method = "dl", maxDist = 2)),
    as.numeric(ain("Mot\u00f6rhead", "Motorhead", method = "dl", useBytes = TRUE, maxDist = 2)),
    as.numeric(ain(c(NA, "abc"), c("aa", "bb", "b"), maxDist = 2)),
    as.numeric(ain(c(NA, "abc"), c(NA, "bb", "b"), maxDist = 2, matchNA = FALSE)),
    as.numeric(ain("survey", c("surgery", "sunny"), method = "lcs", maxDist = 3)),
    as.numeric(ain("abc", "cba", method = "cosine", q = 2, maxDist = 1)),
    as.numeric(ain("Euler", c("Ellery", "Gauss"), method = "soundex", maxDist = 1))
  )
}

fmt <- function(v) {
  if (is.nan(v)) return('"NaN"')
  if (is.na(v)) return("null")
  if (is.infinite(v)) return(if (v > 0) '"Inf"' else '"-Inf"')
  sprintf("%.17g", v)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(vapply(value, fmt, ""), collapse = ","),
  median(elapsed) * 1000
))
