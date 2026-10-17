suppressPackageStartupMessages(library(htmltools))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("htmltools")) == "0.5.9")

example <- "/home/ahmed/killr_projects/killr/packages/htmltools/docs/output/htmlEscape-r.txt"
sample <- "a < b & 'c'"
writeLines(
  c(
    paste0("htmlEscape(\"a < b & 'c'\") returns ", htmlEscape(sample), "."),
    paste0(
      "htmlEscape(\"a < b & 'c'\", attribute = TRUE) returns ",
      htmlEscape(sample, attribute = TRUE),
      "."
    )
  ),
  example
)

piece <- c(
  "a<b>c&d",
  "plain text",
  "say 'hi\"",
  "line1\r\nline2",
  NA_character_,
  "",
  "caf\u00e9 < & > \u2603",
  "&amp; already",
  "it's a \"quote\"",
  ">>>",
  "a\tb",
  "\u00e9&\u00e9"
)
text <- rep(piece, 200)
plain <- rep("nothing to escape", 200)
quotes <- "a'b\"c\r\n<&>"
numbers <- c(1e-4, 1e5, 10000, 0.00015, 2e5, NA, NaN, Inf, -Inf, -0, 1/3)

one <- function() {
  list(
    text = htmlEscape(text),
    attr = htmlEscape(text, TRUE),
    plain = htmlEscape(plain),
    numbers = htmlEscape(numbers),
    integer = htmlEscape(c(100000L, 1L, NA)),
    logical = htmlEscape(c(TRUE, FALSE, NA)),
    mixed = htmlEscape(c("a<", 1e5, TRUE, 100000L)),
    flags = list(
      false = htmlEscape(quotes, FALSE),
      true = htmlEscape(quotes, TRUE),
      zero = htmlEscape(quotes, 0),
      two = htmlEscape(quotes, 2),
      false_word = htmlEscape(quotes, "false"),
      t_word = htmlEscape(quotes, "T")
    ),
    empty = htmlEscape(NULL),
    na = htmlEscape(NA_character_)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"median_ms":%.17g,"value":', median(elapsed) * 1000))
cat(toJSON(value, auto_unbox = FALSE, na = "null", digits = NA))
cat("}\n")
