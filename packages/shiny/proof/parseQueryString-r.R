suppressPackageStartupMessages(library(shiny))

hex <- function(s) {
  if (length(s) == 0 || is.na(s)) s <- ""
  paste(sprintf("%02x", as.integer(charToRaw(s))), collapse = "")
}

fmt <- function(x) {
  if (is.character(x)) {
    return(paste0("s:", hex(x)))
  }
  if (length(x) == 0) return("l:()")
  nms <- names(x)
  if (is.null(nms)) nms <- rep("", length(x))
  parts <- vapply(seq_along(x), function(i) {
    paste0("s:", hex(nms[[i]]), "=", fmt(x[[i]]))
  }, character(1))
  paste0("l:(", paste(parts, collapse = "|"), ")")
}

grab <- function(expr) {
  tryCatch(fmt(eval(expr)), error = function(e) paste0("ERR ", conditionMessage(e)))
}

one <- function() {
  strings <- c(
    "?foo=1&bar=b%20a%20r",
    "?foo=1&bar=b+a%20r&b+a%20z=baz&=nokey&novalue=&=&noequal&end=end",
    "foo=1&bar=b",
    "?foo=1&bar=b",
    "?&a=1&&b=2&",
    "a[i1][j1]=x&b[i1][j1]=y&b[i2][j1]=z",
    "",
    "?",
    "a=b=c",
    "a=%2B%26%3D",
    "k=%C3%A9",
    "k=%E2%82%AC",
    "a=%",
    "a=%2",
    "a=%zz",
    "a=%00",
    "a=%61%00%62",
    "k=A%41B%zzC%41",
    "k=%4%41",
    "k=%%41",
    "k=%41%zz%41",
    "k=%FF",
    "k=%C3",
    "k=%0A",
    "a[b]=1&c=2",
    "a[b][c]=2&a[b]=1",
    "a[b]=1&a[b][c]=2",
    "a=9&a[b]=1",
    "a%5Bb%5D=z",
    "a[b+c]=x",
    "a=1&a=2",
    "a[b]c=1",
    "\u00e9=1",
    "k=+%41"
  )
  parts <- character()
  for (text in strings) {
    parts <- c(
      parts,
      grab(bquote(parseQueryString(.(text)))),
      grab(bquote(parseQueryString(.(text), nested = TRUE)))
    )
  }
  parts <- c(
    parts,
    grab(quote(parseQueryString(NULL))),
    grab(quote(parseQueryString(NULL, nested = TRUE))),
    grab(quote(parseQueryString(character(0)))),
    grab(quote(parseQueryString(c("a=1", "b=2")))),
    grab(quote(parseQueryString(1))),
    grab(quote(parseQueryString(NA_character_)))
  )
  paste(parts, collapse = "\n")
}

value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
shown <- gsub("\n", " / ", value, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
