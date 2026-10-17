suppressPackageStartupMessages(library(stringdist))
if (packageDescription("stringdist")$Version != "0.9.17") stop("expected stringdist 0.9.17")
options(sd_num_thread = 1L)

one <- function() {
  testset <- "name;code
Robert;R163
rupert;R163
Rubin;R150
Ashcraft;A261
asHCroft;A261
Tymczak;T522
Pfister;P236
gutierrez;G362
Jackson;J250
washington;W252
Lee;L000
NA;NA"
  testset <- read.csv2(textConnection(testset), stringsAsFactors = FALSE)
  parts <- list(
    phonetic(testset$name, "soundex"),
    phonetic(testset$name, "soundex", useBytes = TRUE),
    phonetic(c("Euler", "Ellery", "Gauss")),
    phonetic(c("Euler", "Ellery", "Gauss"), useBytes = TRUE),
    phonetic(c(NA, "abc")),
    phonetic(""),
    phonetic(paste0("Mot\u00f6rhead")),
    phonetic(paste0("Mot\u00f6rhead"), useBytes = TRUE),
    phonetic(paste0("\r", "hello")),
    phonetic("Ashcraft", method = "s")
  )
  unlist(parts, use.names = FALSE)
}

quote_json <- function(v) {
  if (is.na(v)) return("null")
  chars <- utf8ToInt(v)
  parts <- character(length(chars))
  for (i in seq_along(chars)) {
    ch <- chars[i]
    if (ch == 34L) {
      parts[i] <- '\\"'
    } else if (ch == 92L) {
      parts[i] <- "\\\\"
    } else if (ch < 32L || ch == 127L) {
      parts[i] <- sprintf("\\u%04x", ch)
    } else {
      parts[i] <- intToUtf8(ch)
    }
  }
  paste0('"', paste0(parts, collapse = ""), '"')
}

fmt <- function(v) {
  if (is.character(v)) return(quote_json(v))
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
