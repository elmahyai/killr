suppressPackageStartupMessages(library(htmltools))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("htmltools")) == "0.5.9")
options(width = 80)

example <- "/home/ahmed/killr_projects/killr/packages/htmltools/docs/output/HTML-r.txt"
marked <- HTML("I like <u>turtles</u>")
joined <- HTML("a", "b", .noWS = "before")
writeLines(
  c(
    paste0("HTML(\"I like <u>turtles</u>\") returns ", marked, "."),
    paste0("HTML(\"a\", \"b\", .noWS = \"before\") returns ", joined, ".")
  ),
  example
)

piece <- c(
  "I like <u>turtles</u>",
  "a < b & 'c'",
  "caf\u00e9",
  "plain",
  NA_character_,
  "",
  "line1\nline2",
  "a\"b\\c"
)
text <- rep(piece, 400)

pack <- function(x) {
  nows <- attr(x, "noWS", exact = TRUE)
  if (is.null(nows)) {
    encoded <- list(type = "null")
  } else {
    encoded <- list(type = typeof(nows), value = nows)
  }
  list(
    text = as.vector(x),
    html = isTRUE(attr(x, "html", exact = TRUE)),
    class = class(x),
    noWS = encoded
  )
}

one <- function() {
  list(
    example = pack(HTML("I like <u>turtles</u>")),
    concat = pack(HTML("a", "b", "c")),
    vec = pack(HTML(c("a", "b"), "c", "d")),
    markup = pack(HTML("a < b & 'c'")),
    numbers = pack(HTML(c(1e-4, 1e5, 10000, 0.00015, 2e5, NA, NaN, Inf, -Inf, -0, 1/3))),
    integer = pack(HTML(c(100000L, 1L, NA))),
    logical = pack(HTML(c(TRUE, FALSE, NA))),
    mixed_int = pack(HTML(c(TRUE, 1L))),
    mixed_dbl = pack(HTML(c(TRUE, 1L, 1.5))),
    mixed_chr = pack(HTML(c(TRUE, "a"))),
    na_mid = pack(HTML(c("a", NA, "b"))),
    empty_mid = pack(HTML("a", "", "b")),
    null_text = pack(HTML(NULL)),
    null_dot = pack(HTML("a", NULL)),
    null_then = pack(HTML(NULL, "a")),
    null_null = pack(HTML(NULL, NULL)),
    char0 = pack(HTML(character(0))),
    empty = pack(HTML("")),
    utf = pack(HTML("caf\u00e9", "\u2603")),
    newline = pack(HTML("a\nb", "c\td")),
    ws = pack(HTML("  a  ", "  b")),
    complex = pack(HTML(c(1+2i, 1-2i))),
    seq_text = pack(HTML(1:3)),
    big = pack(HTML(text)),
    nows_before = pack(HTML("x", .noWS = "before")),
    nows_pair = pack(HTML("x", .noWS = c("before", "after"))),
    nows_out = pack(HTML("x", .noWS = "outside")),
    nows_null = pack(HTML("x", .noWS = NULL)),
    nows_empty = pack(HTML("x", .noWS = character(0))),
    nows_int = pack(HTML("x", .noWS = 1L)),
    nows_na = pack(HTML("x", .noWS = NA_character_)),
    named = pack(HTML("a", foo = "b", bar = "c")),
    dot_seq = pack(HTML("p", 1:5)),
    dot_rev = pack(HTML("p", 5:1)),
    dot_neg = pack(HTML("p", -2:2)),
    dot_gap = pack(HTML("p", c(1L, 2L, 4L))),
    dot_same = pack(HTML("p", c(1L, 1L))),
    dot_dbl_seq = pack(HTML("p", c(1, 2, 3))),
    dot_dbl = pack(HTML("p", c(1e-4, 1e5, NA, NaN))),
    dot_log = pack(HTML("p", c(TRUE, FALSE, NA))),
    dot_chr = pack(HTML("p", c("x", "y"))),
    dot_esc = pack(HTML("p", c("a\"b", "c\\d", "e\nf"))),
    dot_na_chr = pack(HTML("p", c("a", NA))),
    dot_mixed = pack(HTML("p", c(TRUE, "a"))),
    dot_two = pack(HTML(c("a", "b"), c("c", "d"))),
    dot_empty = pack(HTML("a", character(0))),
    dot_cpx = pack(HTML("p", c(1+2i, 1-2i))),
    dot_list = pack(HTML("a", list(b = 1, c = "x"))),
    dot_list_names = pack(HTML("a", list(`a b` = 1, `if` = 2, ok = "z"))),
    dot_list_unnamed = pack(HTML("a", list(1, "x"))),
    already = pack(HTML(HTML("a<b>", .noWS = "before"))),
    named_flag = pack(HTML("a", .named = TRUE)),
    named_flag_value = pack(HTML("a", "b", .named = TRUE)),
    ignore_all = pack(HTML("a", "b", .ignore_empty = "all")),
    homonyms_keep = pack(HTML("a", "b", .homonyms = "keep")),
    preserve_false = pack(HTML("a", "b", .preserve_empty = FALSE)),
    check_false = pack(HTML("a", "b", .check_assign = FALSE)),
    err_missing = tryCatch(HTML(), error = function(e) conditionMessage(e)),
    err_list = tryCatch(HTML(list(b = 1)), error = function(e) conditionMessage(e)),
    err_named = tryCatch(HTML("a", .named = "hello"), error = function(e) conditionMessage(e)),
    err_ignore = tryCatch(HTML("a", .ignore_empty = "nope"), error = function(e) conditionMessage(e)),
    err_hom = tryCatch(HTML("a", .homonyms = "nope"), error = function(e) conditionMessage(e)),
    err_pre = tryCatch(HTML("a", .preserve_empty = "x"), error = function(e) conditionMessage(e)),
    err_chk = tryCatch(HTML("a", .check_assign = "x"), error = function(e) conditionMessage(e))
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
cat(toJSON(value, auto_unbox = TRUE, na = "null", digits = NA))
cat("}\n")
