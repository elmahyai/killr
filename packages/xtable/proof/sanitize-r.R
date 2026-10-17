suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")
options(width = 80)

example <- "/home/ahmed/killr_projects/killr/packages/xtable/docs/output/sanitize-r.txt"
insane <- c("&", ">", ">", "_", "%", "$", "\\", "#", "^", "~", "{", "}")
names(insane) <- c(
  "Ampersand", "Greater than", "Less than",
  "Underscore", "Percent", "Dollar",
  "Backslash", "Hash", "Caret", "Tilde",
  "Left brace", "Right brace"
)
sink(example)
print(sanitize(insane, type = "latex"))
insane <- c("&", ">", "<")
names(insane) <- c("Ampersand", "Greater than", "Less than")
print(sanitize(insane, type = "html"))
sink()

piece <- c(
  "&", ">", "<", "|", "{", "}", "%", "_", "#", "^", "~", "$", "\\",
  "SANITIZE.BACKSLASH",
  "\\$><|{}%&_#^~",
  "a&b<c>d",
  "&<>&",
  "100%",
  "a_b",
  "",
  NA_character_,
  "NA",
  "café & naïve",
  "a&\nb<c>",
  "xSANITIZE.BACKSLASHy",
  "\\SANITIZE.BACKSLASH",
  "already &amp;",
  "p|q",
  "~^#_",
  "no specials",
  "\\&\\%\\_",
  "a^b",
  "~~~"
)
text <- rep(piece, 800)
example_latex <- c("&", ">", ">", "_", "%", "$", "\\", "#", "^", "~", "{", "}")
names(example_latex) <- c(
  "Ampersand", "Greater than", "Less than",
  "Underscore", "Percent", "Dollar",
  "Backslash", "Hash", "Caret", "Tilde",
  "Left brace", "Right brace"
)
example_html <- c("&", ">", "<")
names(example_html) <- c("Ampersand", "Greater than", "Less than")
numbers <- c(
  1e-4, 1e5, 10000, 0.00015, 2e5, NA, NaN, Inf, -Inf, -0, 1 / 3,
  1e16, 1e15, 1e-20, 0.1, 10, 0.001, 1e4, 123456789012345,
  1.23456789012345e-8
)
message_of <- function(expr) {
  tryCatch(expr, error = function(e) conditionMessage(e))
}

one <- function() {
  latex_example <- sanitize(example_latex, "latex")
  html_example <- sanitize(example_html, "html")
  list(
    latex = sanitize(text, "latex"),
    html = sanitize(text, "html"),
    default = sanitize(text),
    other = sanitize(c("a&b<c>d"), "foo"),
    upper = sanitize(c("a&b", "c<d"), "HTML"),
    example_latex = unname(latex_example),
    example_latex_names = names(latex_example),
    example_html = unname(html_example),
    example_html_names = names(html_example),
    numbers = sanitize(numbers),
    integer = sanitize(c(100000L, 1L, NA_integer_, -2147483647L, 0L)),
    logical = sanitize(c(TRUE, FALSE, NA)),
    mixed = sanitize(c("a<", 1e5, TRUE, 100000L, NA)),
    empty = sanitize(character(0)),
    null = sanitize(NULL),
    na = sanitize(NA_character_),
    single = sanitize("a&b"),
    true_type = sanitize("a&b", TRUE),
    one_type = sanitize("a&b", "latex"),
    plain_names = names(sanitize("a&b")),
    err_null = message_of(sanitize("a", NULL)),
    err_na = message_of(sanitize("a", NA)),
    err_len = message_of(sanitize("a", c("latex", "html"))),
    nan_type = sanitize("a&b", NaN),
    err_empty_type = message_of(sanitize("a", character(0)))
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
cat(toJSON(value, auto_unbox = FALSE, na = "null", null = "null", digits = NA))
cat("}\n")
