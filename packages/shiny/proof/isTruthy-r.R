suppressPackageStartupMessages(library(shiny))

show <- function(x) {
  tryCatch(
    if (isTRUE(isTruthy(x))) "TRUE" else "FALSE",
    error = function(e) paste0("ERR ", conditionMessage(e))
  )
}

one <- function() {
  btn <- function(n) structure(n, class = "shinyActionButtonValue")
  cases <- list(
    NULL,
    FALSE,
    TRUE,
    "",
    " ",
    "0",
    "NA",
    character(0),
    logical(0),
    numeric(0),
    integer(0),
    complex(0),
    raw(0),
    NA,
    NA_integer_,
    NA_real_,
    NA_complex_,
    NA_character_,
    c(NA, NA, FALSE),
    c(FALSE),
    0,
    0L,
    1:3,
    c("a", "b"),
    c(NA, NA, TRUE),
    c(FALSE, FALSE, TRUE),
    try(stop("boom"), silent = TRUE),
    list(),
    matrix(),
    matrix(FALSE, 1, 1),
    NaN,
    Inf,
    -Inf,
    0+0i,
    as.raw(0),
    factor("a"),
    factor(NA),
    factor(character(0)),
    data.frame(),
    btn(0L),
    btn(1L),
    btn(0),
    btn("0"),
    btn("a"),
    btn("0.0"),
    c("", ""),
    c("", "a"),
    c(NA_character_, ""),
    c(NA_character_, "a"),
    c(NA, FALSE),
    c(FALSE, FALSE),
    c(0, NA),
    c(NaN, NaN),
    c(NaN, 1),
    btn(c(0L, 1L)),
    c(a = FALSE),
    -0,
    structure(list("err"), class = "try-error"),
    c("  ", NA),
    as.raw(c(0, 1))
  )
  paste(vapply(cases, show, character(1)), collapse = "\n")
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
