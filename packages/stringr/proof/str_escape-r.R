.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageVersion("stringr") == "1.6.0")
stopifnot(packageVersion("stringi") == "1.8.9")

writeLines(
  paste0("str_escape(\".\") returns ", str_escape("."), "."),
  "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_escape-r.txt"
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

piece <- c("a.b", "(x)", NA, "", "\\", "a^b$", ".^$\\|*+?{}[]()")

one <- function() {
  list(
    main = str_escape(rep(piece, 20)),
    dot = str_escape("."),
    many = str_escape(c("a.b", "(x)", NA, "", "\\", "a^b$")),
    all = str_escape(".^$\\|*+?{}[]()"),
    names = str_escape(c(a = ".", b = "?")),
    empty = str_escape(character()),
    null = str_escape(NULL)
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
