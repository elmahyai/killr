suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

one <- function() {
  ouml <- intToUtf8(0x00F6)
  x <- c("Motorhead", paste0("Mot", ouml, "rhead"))
  parts <- list(
    printable_ascii(x),
    printable_ascii("abc\r"),
    printable_ascii(NA_character_),
    printable_ascii(c(NA_character_, "abc")),
    printable_ascii(c(NA, "abc")),
    printable_ascii(character(0)),
    printable_ascii("\t"),
    printable_ascii("hello\tworld"),
    printable_ascii(""),
    printable_ascii(c("", " ", "A", "!")),
    printable_ascii("Mot\u00f6rhead"),
    printable_ascii("abc\n"),
    printable_ascii("ASCII only 123"),
    printable_ascii(" !\"#$%&'()*+,./:;<=>?@[\\]^_`{|}~-"),
    printable_ascii(c("Robert", "rupert", "Rubin")),
    printable_ascii(paste0("\r", "hello")),
    printable_ascii(paste0("hello", "\r"))
  )
  as.numeric(unlist(parts, use.names = FALSE))
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
