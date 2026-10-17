.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("stringr") == "1.6.0")
stopifnot(packageVersion("stringi") == "1.8.9")

x <- rawToChar(as.raw(177))
writeLines(
  c(
    paste0("str_conv(x, \"ISO-8859-2\") returns ", str_conv(x, "ISO-8859-2"), "."),
    paste0("str_conv(x, \"ISO-8859-1\") returns ", str_conv(x, "ISO-8859-1"), ".")
  ),
  "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_conv-r.txt"
)

norm <- function(x) {
  if (is.null(x)) return(list())
  if (is.list(x)) {
    out <- lapply(x, norm)
    if (is.null(names(x))) return(out)
    return(list(data = unname(out), names = names(x)))
  }
  if (is.null(names(x))) return(unname(x))
  list(data = unname(x), names = names(x))
}

one <- function() {
  x <- rawToChar(as.raw(177))
  list(
    main = str_conv(rep(x, 40), "ISO-8859-2"),
    latin2 = str_conv(x, "ISO-8859-2"),
    latin1 = str_conv(x, "ISO-8859-1"),
    utf8 = str_conv("a", "UTF-8"),
    letter = str_conv("\u0105", "UTF-8"),
    null = str_conv(NULL, "UTF-8"),
    empty = str_conv(character(), "UTF-8"),
    na = str_conv(NA, "UTF-8"),
    two = str_conv(c(x, x), "ISO-8859-1"),
    named = str_conv(c(p = x), "ISO-8859-2")
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
body <- jsonlite::toJSON(lapply(value, norm), auto_unbox = FALSE, na = "null", null = "null", digits = 16)
ms <- jsonlite::toJSON(median(elapsed) * 1000, auto_unbox = TRUE, digits = 16)
cat(paste0("{\"value\":", body, ",\"median_ms\":", ms, "}\n"))
