suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

base <- c(
  "1e5", "1E10", "-2.5e+10", "1.2e-03", "not", "1e5e6", NA_character_, "",
  "$1e5$", "1e+05", "1.0e00", "3e-0", "1e-3", "10000", "a-b", "1-2", "-1"
)
names(base) <- letters[seq_along(base)]

message_of <- function(expr) {
  tryCatch(expr, error = function(e) conditionMessage(e))
}

one <- function() {
  list(
    default = sanitize.numbers(base, "latex"),
    html = sanitize.numbers(base, "html"),
    html_opts = sanitize.numbers(base, "html", TRUE, TRUE),
    neg = sanitize.numbers(base, "latex", math.style.negative = TRUE),
    exp = sanitize.numbers(base, "latex", math.style.exponents = TRUE),
    both = sanitize.numbers(base, "latex", TRUE, TRUE),
    numeric = sanitize.numbers(c(1e5, 1000, -1), "latex", TRUE, TRUE),
    numeric_html = sanitize.numbers(1e5, "html"),
    named = sanitize.numbers(base, "latex", TRUE, TRUE),
    named_names = names(sanitize.numbers(base, "latex", TRUE, TRUE)),
    empty = sanitize.numbers(character(0), "latex"),
    single = sanitize.numbers("1e5", "latex", FALSE, TRUE),
    err_type_len = message_of(sanitize.numbers(base, c("latex", "html"))),
    err_type_na = message_of(sanitize.numbers(base, NA)),
    err_neg_na = message_of(sanitize.numbers("1", "latex", math.style.negative = NA)),
    err_exp_na = message_of(sanitize.numbers("1", "latex", math.style.exponents = NA)),
    err_exp_str = message_of(
      sanitize.numbers("1e5", "latex", math.style.exponents = "$$")
    ),
    err_neg_len = message_of(
      sanitize.numbers("1", "latex", math.style.negative = c(TRUE, FALSE))
    ),
    exp_num = sanitize.numbers("1e5", "latex", FALSE, 1),
    neg_chr = sanitize.numbers("-1", "latex", "TRUE", "FALSE")
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
