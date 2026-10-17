suppressPackageStartupMessages(library(htmltools))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("htmltools")) == "0.5.9")
options(width = 200)

example <- "/home/ahmed/killr_projects/killr/packages/htmltools/docs/output/tagList-r.txt"
sink(example)
print(tagList(
  h1("Title"),
  h2("Header text", style = "color: red;"),
  p("Text here")
))
sink()

sep <- "\x1f"

join_names <- function(nms) {
  if (length(nms) == 0) "" else paste(nms, collapse = sep)
}

pack_one <- function(x) {
  if (is.null(x)) return(list(type = "null"))
  if (is.symbol(x)) {
    return(list(type = "symbol", value = paste(as.character(x), collapse = "")))
  }
  if (inherits(x, "shiny.tag.list")) return(pack_tag(x))
  if (is.list(x)) {
    nms <- names(x)
    return(list(
      type = "list",
      n = length(x),
      names = if (is.null(nms)) NULL else join_names(nms),
      items = unname(lapply(x, pack_one))
    ))
  }
  kind <- typeof(x)
  if (length(x) == 1 && is.na(x) && !(kind == "double" && is.nan(x))) {
    return(list(type = kind, missing = TRUE))
  }
  if (length(x) == 1) return(list(type = kind, value = x))
  list(type = kind, n = length(x), value = as.list(x))
}

pack_tag <- function(x) {
  list(
    type = "tagList",
    class = class(x),
    n = length(x),
    names = join_names(names(x)),
    items = unname(lapply(x, pack_one))
  )
}

run <- function(expr) {
  warnings <- character()
  value <- withCallingHandlers(
    tryCatch(expr, error = function(e) e),
    warning = function(w) {
      warnings <<- c(warnings, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  )
  note <- paste(warnings, collapse = "\n---\n")
  if (inherits(value, "error")) {
    list(error = conditionMessage(value), value = NULL, warnings = note)
  } else {
    list(error = NULL, value = pack_tag(value), warnings = note)
  }
}

one <- function() {
  foo <- 10
  list(
    empty = run(tagList()),
    one = run(tagList("hi")),
    two = run(tagList("one", "two")),
    nested = run(tagList("one", tagList("three"))),
    named = run(tagList(a = 1, b = "x")),
    dup = run(tagList(a = 1, a = 2)),
    null = run(tagList(NULL)),
    null_mid = run(tagList("a", NULL, "b")),
    types = run(tagList(1, 2L, TRUE, FALSE, NA, NULL, "a", "")),
    utf = run(tagList("caf\u00e9")),
    list_one = run(tagList(list("one"))),
    list_named = run(tagList(list(b = 1, c = "x"))),
    trail = run(tagList("hi", )),
    trail_preserve = run(tagList("hi", , .preserve_empty = TRUE)),
    ignore_all = run(tagList(, "a", , "b", , .ignore_empty = "all")),
    preserve_mid = run(tagList("a", , "b", .preserve_empty = TRUE)),
    preserve_na = run(tagList("a", , "b", .preserve_empty = NA, .ignore_empty = "none")),
    preserve_vec = run(tagList("a", , "b", .preserve_empty = c(TRUE, FALSE), .ignore_empty = "none")),
    splice_named = run(tagList(!!!list(a = 1, b = 2), c = 3)),
    splice_atomic = run(tagList("p", !!!c("x", "y"), "z")),
    splice_null = run(tagList(!!!NULL, "z")),
    splice_empty = run(tagList(!!!list(), "z")),
    splice_tag = run(tagList(!!!tagList(a = "a", b = "b"), "c")),
    hom_first = run(tagList(1, a = 2, 1, a = 3, .homonyms = "first")),
    hom_last = run(tagList(1, a = 2, 1, a = 3, .homonyms = "last")),
    hom_keep = run(tagList(a = 1, a = 2, .homonyms = "keep")),
    hom_splice_last = run(tagList(a = 1, !!!list(a = 9, b = 8), .homonyms = "last")),
    named_expr = run(tagList(1.0 + 2.0, foo, "x", 2L, TRUE, NULL, 1e-4, .named = TRUE)),
    named_splice = run(tagList(!!!list("x", 2.5, 10L, TRUE, NULL), .named = TRUE)),
    named_null = run(tagList("a", .named = NULL)),
    named_dup = run(tagList(1, 1, .named = TRUE, .homonyms = "error")),
    big = run(do.call(tagList, c(as.list(0.5 * (1:2000)), list(a = "end")))),
    assign_true = run(tagList(assigned <- 1, .check_assign = TRUE)),
    assign_two = run(tagList(a <- 1, b <- 2, .check_assign = TRUE)),
    assign_false = run(tagList(c <- 1, .check_assign = FALSE)),
    assign_default = run(tagList(d <- 1)),
    assign_na = run(tagList(q <- 1, .check_assign = NA)),
    err_only_empty = run(tagList(,)),
    err_two_trail = run(tagList("a", , )),
    err_lead = run(tagList(, "one", )),
    err_mid = run(tagList("a", , "b")),
    err_splice_mid = run(tagList(!!!list(1, 2), , "b")),
    err_splice_trail = run(tagList("a", !!!list(1), , )),
    err_hom_nope = run(tagList(a = 1, .homonyms = "nope")),
    err_hom_f = run(tagList(a = 1, .homonyms = "f")),
    err_ignore_nope = run(tagList(.ignore_empty = "nope")),
    err_ignore_t = run(tagList(.ignore_empty = "t")),
    err_ignore_vec = run(tagList(.ignore_empty = c("all", "none"))),
    err_named_hello = run(tagList(.named = "hello")),
    err_named_na = run(tagList(.named = NA)),
    err_preserve_chr = run(tagList(.preserve_empty = "x")),
    err_preserve_null = run(tagList(.preserve_empty = NULL)),
    err_preserve_int = run(tagList(.preserve_empty = 1L)),
    err_preserve_dbl = run(tagList(.preserve_empty = 1)),
    err_check_chr = run(tagList(.check_assign = "x")),
    err_hom_dup = run(tagList(a = 1, a = 2, .homonyms = "error")),
    err_hom_three = run(tagList(a = 1, a = 2, a = 3, .homonyms = "error")),
    err_hom_two = run(tagList(a = 1, b = 2, a = 3, b = 4, .homonyms = "error")),
    err_preserve_false = run(tagList("a", , "b", .preserve_empty = c(FALSE, TRUE), .ignore_empty = "none")),
    err_hom_drop = run(tagList(a = 1, , a = 2, .ignore_empty = "all", .homonyms = "error")),
    err_hom_splice = run(tagList(a = 1, !!!list(a = 2), .homonyms = "error"))
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
cat(toJSON(value, auto_unbox = TRUE, na = "null", null = "null", digits = NA))
cat("}\n")
