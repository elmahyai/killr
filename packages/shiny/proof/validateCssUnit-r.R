suppressPackageStartupMessages(library(shiny))
stopifnot(identical(as.character(packageVersion("shiny")), "1.14.0"))

encode <- function(x) {
  if (is.null(x)) return("NULL")
  if (is.list(x)) {
    if (length(x) == 0) return("L()")
    parts <- vapply(seq_along(x), function(i) encode(x[[i]]), character(1))
    return(paste0("L(", paste(parts, collapse = ","), ")"))
  }
  if (is.character(x)) {
    if (length(x) == 1 && is.na(x)) return("NA_character_")
    s <- gsub("\n", "\\n", x[[1]], fixed = TRUE)
    s <- gsub("\t", "\\t", s, fixed = TRUE)
    return(paste0("C(", s, ")"))
  }
  if (is.integer(x)) {
    if (length(x) == 1 && is.na(x)) return("NA_integer_")
    return(paste0("I(", x[[1]], ")"))
  }
  if (is.complex(x)) {
    if (length(x) == 1 && is.na(x)) return("NA_complex_")
    return("CX")
  }
  if (is.logical(x)) {
    if (length(x) == 1 && is.na(x)) return("NA")
    return(if (isTRUE(x[[1]])) "TRUE" else "FALSE")
  }
  if (is.double(x)) {
    if (length(x) == 1 && is.nan(x)) return("NaN")
    if (length(x) == 1 && is.na(x)) return("NA_real_")
    return(paste0("D(", as.character(x[[1]]), ")"))
  }
  paste0("O(", paste(class(x), collapse = ","), ")")
}

show <- function(f) {
  tryCatch(encode(f()), error = function(e) {
    msg <- conditionMessage(e)
    msg <- gsub("\n", "\\n", msg, fixed = TRUE)
    msg <- gsub("\t", "\\t", msg, fixed = TRUE)
    paste0("ERR ", msg)
  })
}

one <- function() {
  calls <- list(
    function() validateCssUnit(NULL),
    function() validateCssUnit(NA),
    function() validateCssUnit(NA_integer_),
    function() validateCssUnit(NA_real_),
    function() validateCssUnit(NA_character_),
    function() validateCssUnit(NA_complex_),
    function() validateCssUnit(NaN),
    function() validateCssUnit(character(0)),
    function() validateCssUnit(numeric(0)),
    function() validateCssUnit(integer(0)),
    function() validateCssUnit(logical(0)),
    function() validateCssUnit(c(NA, NA)),
    function() validateCssUnit(c(1, 2)),
    function() validateCssUnit(1:3),
    function() validateCssUnit(c("1px", "2px")),
    function() validateCssUnit(FALSE),
    function() validateCssUnit(TRUE),
    function() validateCssUnit(list()),
    function() validateCssUnit(list(1)),
    function() validateCssUnit(list(NA)),
    function() validateCssUnit(list(NULL)),
    function() validateCssUnit(list(NaN)),
    function() validateCssUnit(list(NA_real_)),
    function() validateCssUnit(list(c(NA_real_, 1))),
    function() validateCssUnit(""),
    function() validateCssUnit(" "),
    function() validateCssUnit("auto"),
    function() validateCssUnit("AUTO"),
    function() validateCssUnit("inherit"),
    function() validateCssUnit("fit-content"),
    function() validateCssUnit("fit-content(20px)"),
    function() validateCssUnit("10%"),
    function() validateCssUnit("400px"),
    function() validateCssUnit(400),
    function() validateCssUnit(400L),
    function() validateCssUnit(c(a = 400)),
    function() validateCssUnit(1.5),
    function() validateCssUnit(-10),
    function() validateCssUnit(-0),
    function() validateCssUnit(0),
    function() validateCssUnit(0L),
    function() validateCssUnit(Inf),
    function() validateCssUnit(-Inf),
    function() validateCssUnit(1e-4),
    function() validateCssUnit(1e5),
    function() validateCssUnit(100000L),
    function() validateCssUnit(pi),
    function() validateCssUnit(2^53),
    function() validateCssUnit(2^53 + 2),
    function() validateCssUnit(2^60),
    function() validateCssUnit(1e15),
    function() validateCssUnit(1e16),
    function() validateCssUnit(1e-20),
    function() validateCssUnit(1e308),
    function() validateCssUnit(0.00012),
    function() validateCssUnit(-0.00012),
    function() validateCssUnit(1/3),
    function() validateCssUnit(0.3),
    function() validateCssUnit(9.99999999999999e-05),
    function() validateCssUnit("007"),
    function() validateCssUnit("100000"),
    function() validateCssUnit("00"),
    function() validateCssUnit("0"),
    function() validateCssUnit("0.0"),
    function() validateCssUnit(".5"),
    function() validateCssUnit(".5px"),
    function() validateCssUnit("0.5px"),
    function() validateCssUnit("10.0px"),
    function() validateCssUnit("5."),
    function() validateCssUnit("5.px"),
    function() validateCssUnit("1.0"),
    function() validateCssUnit("1."),
    function() validateCssUnit("calc(100% - 10px)"),
    function() validateCssUnit("calc()"),
    function() validateCssUnit("calc("),
    function() validateCssUnit("calc())"),
    function() validateCssUnit("calc(a\nb)"),
    function() validateCssUnit("1in"),
    function() validateCssUnit("2.5vmin"),
    function() validateCssUnit("10vh"),
    function() validateCssUnit("1ch"),
    function() validateCssUnit("1em"),
    function() validateCssUnit("1ex"),
    function() validateCssUnit("1rem"),
    function() validateCssUnit("1pt"),
    function() validateCssUnit("1pc"),
    function() validateCssUnit("1cm"),
    function() validateCssUnit("1mm"),
    function() validateCssUnit("1vw"),
    function() validateCssUnit("1vmax"),
    function() validateCssUnit("1%"),
    function() validateCssUnit("01px"),
    function() validateCssUnit("10.5%"),
    function() validateCssUnit(".5%"),
    function() validateCssUnit("foo"),
    function() validateCssUnit("+5"),
    function() validateCssUnit("+5px"),
    function() validateCssUnit("1e2"),
    function() validateCssUnit("1e2px"),
    function() validateCssUnit("-10px"),
    function() validateCssUnit("-1"),
    function() validateCssUnit("10PX"),
    function() validateCssUnit("10px "),
    function() validateCssUnit(" 10px"),
    function() validateCssUnit("auto "),
    function() validateCssUnit("vmin"),
    function() validateCssUnit("10v"),
    function() validateCssUnit("\t10px"),
    function() validateCssUnit("10\n"),
    function() validateCssUnit("\u0661\u0662\u0663"),
    function() validateCssUnit(1 + 0i),
    function() validateCssUnit(as.raw(0)),
    function() validateCssUnit(raw(0)),
    function() validateCssUnit("999999999999999999"),
    function() validateCssUnit(paste(rep("9", 400), collapse = ""))
  )
  paste(vapply(calls, show, character(1)), collapse = "\n")
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
