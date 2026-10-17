.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

json_str <- function(s) {
  chars <- strsplit(enc2utf8(s), "")[[1]]
  parts <- character(length(chars))
  for (i in seq_along(chars)) {
    cp <- utf8ToInt(chars[[i]])
    parts[[i]] <- if (cp == 34) paste0("\\", '"')
      else if (cp == 92) paste0("\\", "\\")
      else if (cp == 10) paste0("\\", "n")
      else if (cp == 13) paste0("\\", "r")
      else if (cp == 9) paste0("\\", "t")
      else if (cp < 32 || cp == 127) sprintf("\\u%04x", cp)
      else chars[[i]]
  }
  paste0('"', paste(parts, collapse = ""), '"')
}

flat <- function(x) {
  paste(vapply(x, json_str, ""), collapse = "|")
}

esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s
}

one <- function() {
  cities1 <- ASCIIfy(c("S\u00e3o Paulo", "Reykjav\u00edk"), 1)
  cities2 <- ASCIIfy(c("S\u00e3o Paulo", "Reykjav\u00edk"), 2)
  athens <- ASCIIfy("\u0391\u03b8\u03ae\u03bd\u03b1")
  bulk1 <- ASCIIfy(
    c("a", "S\u00e3o Paulo", "\u0391\u03b8\u03ae\u03bd\u03b1", "caf\u00e9", "z\\x", ""),
    bytes = 1
  )
  bulk2 <- ASCIIfy(
    c("a", "S\u00e3o Paulo", "\u0391\u03b8\u03ae\u03bd\u03b1", "caf\u00e9", "z\\x", ""),
    bytes = 2
  )
  singles <- c(
    ASCIIfy("z", 1),
    ASCIIfy("\u00e9", 1),
    ASCIIfy("\u00e9", 2),
    ASCIIfy("\u0391", 1),
    ASCIIfy("\u0391", 2),
    ASCIIfy("\u03fe", 1),
    ASCIIfy("\u03fe", 2)
  )
  c(cities1, cities2, athens, bulk1, bulk2, singles)
}

value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
