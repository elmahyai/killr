suppressPackageStartupMessages(library(htmltools))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("htmltools")) == "0.5.9")

example <- "/home/ahmed/killr_projects/killr/packages/htmltools/docs/output/htmlDependency-r.txt"

fmt_dep <- function(prefix, x) {
  src <- paste0(
    names(x$src),
    "=",
    vapply(x$src, function(el) paste(as.character(el), collapse = " "), character(1)),
    collapse = ","
  )
  script <- if (is.null(x$script)) "NULL" else paste(as.character(x$script), collapse = " ")
  style <- if (is.null(x$stylesheet)) "NULL" else paste(as.character(x$stylesheet), collapse = " ")
  flag <- if (isTRUE(x$all_files)) "TRUE" else if (identical(x$all_files, FALSE)) "FALSE" else as.character(x$all_files)
  paste0(
    prefix, " returns ", as.character(x$name), " ", as.character(x$version),
    " src=", src, " script=", script, " stylesheet=", style, " all_files=", flag, "."
  )
}

js <- htmlDependency(
  "jqueryui", "1.11.4", c(href = "shared/jqueryui"),
  script = "jquery-ui.min.js"
)
css <- htmlDependency(
  "font-awesome", "4.5.0", c(href = "shared/font-awesome"),
  stylesheet = "css/font-awesome.min.css"
)
writeLines(
  c(
    fmt_dep(
      "htmlDependency(\"jqueryui\", \"1.11.4\", c(href = \"shared/jqueryui\"), script = \"jquery-ui.min.js\")",
      js
    ),
    fmt_dep(
      "htmlDependency(\"font-awesome\", \"4.5.0\", c(href = \"shared/font-awesome\"), stylesheet = \"css/font-awesome.min.css\")",
      css
    )
  ),
  example
)

encode_names <- function(nms) {
  if (is.null(nms)) return(NULL)
  lapply(nms, function(n) if (is.na(n)) list(na = TRUE) else n)
}

encode_el <- function(el, type) {
  if (type == "double") {
    if (is.nan(el)) return(list(nan = TRUE))
    if (is.na(el)) return(list(na = TRUE))
    if (is.infinite(el)) return(list(inf = if (el > 0) 1L else -1L))
    return(as.character(el))
  }
  if (is.na(el)) return(list(na = TRUE))
  if (type == "complex") return(as.character(el))
  el
}

encode_atomic <- function(x) {
  type <- typeof(x)
  n <- length(x)
  data <- vector("list", n)
  if (n > 0L) {
    for (i in seq_len(n)) data[[i]] <- encode_el(x[[i]], type)
  }
  list(t = type, names = encode_names(names(x)), data = data)
}

encode <- function(x) {
  if (is.null(x)) return(list(t = "null"))
  if (is.list(x)) {
    out <- list(
      t = "list",
      names = encode_names(names(x)),
      items = unname(lapply(x, encode))
    )
    cls <- class(x)
    if (!(length(cls) == 1L && identical(cls, "list"))) out$class <- cls
    return(out)
  }
  encode_atomic(x)
}

call_dep <- function(expr, namespace = FALSE) {
  expr <- substitute(expr)
  envir <- if (isTRUE(namespace)) getNamespace("htmltools") else parent.frame()
  warns <- character()
  res <- tryCatch(
    withCallingHandlers(
      list(ok = TRUE, value = eval(expr, envir)),
      warning = function(w) {
        warns <<- c(warns, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(e) list(ok = FALSE, error = conditionMessage(e))
  )
  res$warning <- warns
  res
}

encode_run <- function(res) {
  list(
    error = if (isTRUE(res$ok)) NULL else res$error,
    warning = if (length(res$warning) == 0) NULL else as.list(res$warning),
    value = if (isTRUE(res$ok)) encode(res$value) else NULL
  )
}

na_src <- c(a = "p", "q")
names(na_src)[2] <- NA_character_
space_src <- c("p")
names(space_src) <- " "

one <- function() {
  list(
    example_js = call_dep(htmlDependency("jqueryui", "1.11.4", c(href = "shared/jqueryui"), script = "jquery-ui.min.js")),
    example_css = call_dep(htmlDependency("font-awesome", "4.5.0", c(href = "shared/font-awesome"), stylesheet = "css/font-awesome.min.css")),
    unnamed = call_dep(htmlDependency("a", "1", "path")),
    unnamed_vec = call_dep(htmlDependency("a", "1", c("p", "q"))),
    href = call_dep(htmlDependency("a", "1", c(href = "/"))),
    both = call_dep(htmlDependency("a", "1", c(file = "p", href = "u"))),
    mixed_empty = call_dep(htmlDependency("a", "1", c(file = "p", "u"))),
    leading_empty = call_dep(htmlDependency("a", "1", c("p", href = "u"))),
    custom_name = call_dep(htmlDependency("a", "1", c(foo = "p"))),
    list_both = call_dep(htmlDependency("a", "1", list(file = "p", href = "u", "z"))),
    empty_src = call_dep(htmlDependency("a", "1", character(0))),
    empty_list = call_dep(htmlDependency("a", "1", list())),
    null_src = call_dep(htmlDependency("a", "1", NULL)),
    keep_null = call_dep(htmlDependency("a", "1", list(file = NULL, href = "u"))),
    dup_file = call_dep(htmlDependency("a", "1", c("a", "b"))),
    na_logical = call_dep(htmlDependency("a", "1", NA)),
    na_href = call_dep(htmlDependency("a", "1", list(href = NA))),
    na_character = call_dep(htmlDependency("a", "1", c("x", NA_character_))),
    abs_path = call_dep(htmlDependency("a", "1", "/tmp/x")),
    empty_path = call_dep(htmlDependency("a", "1", "")),
    num_src = call_dep(htmlDependency("a", "1", c(1, 2))),
    logical_src = call_dep(htmlDependency("a", "1", TRUE)),
    na_name_src = call_dep(htmlDependency("a", "1", na_src)),
    space_name = call_dep(htmlDependency("a", "1", space_src)),
    ver_num = call_dep(htmlDependency("a", 1.11, "p")),
    ver_int = call_dep(htmlDependency("a", 1L, "p")),
    ver_sci = call_dep(htmlDependency("a", 1e5, "p")),
    ver_small = call_dep(htmlDependency("a", 1e-4, "p")),
    ver_true = call_dep(htmlDependency("a", TRUE, "p")),
    ver_false = call_dep(htmlDependency("a", FALSE, "p")),
    ver_nan = call_dep(htmlDependency("a", NaN, "p")),
    ver_inf = call_dep(htmlDependency("a", Inf, "p")),
    ver_neginf = call_dep(htmlDependency("a", -Inf, "p")),
    ver_half = call_dep(htmlDependency("a", 0.5, "p")),
    ver_complex = call_dep(htmlDependency("a", 1 + 2i, "p")),
    ver_complex_neg = call_dep(htmlDependency("a", 1 - 2i, "p")),
    ver_complex_sci = call_dep(htmlDependency("a", 1 + 1e5i, "p")),
    ver_complex_small = call_dep(htmlDependency("a", 1e-4 + 2i, "p")),
    name_int = call_dep(htmlDependency(1L, "1", "p")),
    name_dbl = call_dep(htmlDependency(1.5, "1", "p")),
    name_true = call_dep(htmlDependency(TRUE, "1", "p")),
    name_nan = call_dep(htmlDependency(NaN, "1", "p")),
    name_inf = call_dep(htmlDependency(Inf, "1", "p")),
    name_neginf = call_dep(htmlDependency(-Inf, "1", "p")),
    name_space = call_dep(htmlDependency("a b", "1", "p")),
    name_dot = call_dep(htmlDependency("a.b", "1", "p")),
    name_dash = call_dep(htmlDependency("font-awesome", "1", "p")),
    name_blank = call_dep(htmlDependency(" ", "1", "p")),
    name_unicode = call_dep(htmlDependency("caf\u00e9", "1", "p")),
    all_false = call_dep(htmlDependency("a", "1", "p", all_files = FALSE)),
    all_na = call_dep(htmlDependency("a", "1", "p", all_files = NA)),
    all_zero = call_dep(htmlDependency("a", "1", "p", all_files = 0)),
    all_int = call_dep(htmlDependency("a", "1", "p", all_files = 0L)),
    package = call_dep(htmlDependency("a", "1", "p", package = "htmltools")),
    package_empty = call_dep(htmlDependency("a", "1", "p", package = "")),
    meta = call_dep(htmlDependency("a", "1", "p", meta = list(name = "viewport", content = "width=device-width"))),
    meta_empty = call_dep(htmlDependency("a", "1", "p", meta = list())),
    script_vec = call_dep(htmlDependency("a", "1", "p", script = c("a.js", "b.js"))),
    script_list = call_dep(htmlDependency("a", "1", "p", script = list(src = "a.js", integrity = "h", defer = NA))),
    script_empty = call_dep(htmlDependency("a", "1", "p", script = character(0))),
    head = call_dep(htmlDependency("a", "1", "p", head = "<script>alert(1)</script>")),
    attachment = call_dep(htmlDependency("a", "1", "p", attachment = list(foo = "a.txt", "b.txt"))),
    style_null = call_dep(htmlDependency("a", "1", "p", stylesheet = NULL)),
    err_empty_name = call_dep(htmlDependency("", "1", "x")),
    err_slash_name = call_dep(htmlDependency("a/b", "1", "x")),
    err_bslash_name = call_dep(htmlDependency("a\\b", "1", "x")),
    err_empty_ver = call_dep(htmlDependency("a", "", "x")),
    err_slash_ver = call_dep(htmlDependency("a", "1/2", "x")),
    err_bslash_ver = call_dep(htmlDependency("a", "1\\2", "x")),
    err_two_name = call_dep(htmlDependency(c("a", "b"), "1", "x")),
    err_two_ver = call_dep(htmlDependency("a", c("1", "2"), "x")),
    err_na_name = call_dep(htmlDependency(NA, "1", "x")),
    err_na_ver = call_dep(htmlDependency("a", NA, "x")),
    err_null_name = call_dep(htmlDependency(NULL, "1", "x")),
    err_null_ver = call_dep(htmlDependency("a", NULL, "x")),
    err_char0_name = call_dep(htmlDependency(character(0), "1", "x")),
    err_char0_ver = call_dep(htmlDependency("a", character(0), "x")),
    err_missing = call_dep(htmlDependency()),
    err_missing_ver = call_dep(htmlDependency("a")),
    err_missing_src = call_dep(htmlDependency("a", "1")),
    err_missing_name = call_dep(htmlDependency(version = "1", src = "p")),
    ns_abs = call_dep(htmlDependency("a", "1", "/tmp/x"), TRUE),
    ns_rel = call_dep(htmlDependency("a", "1", "rel/path"), TRUE),
    ns_url = call_dep(htmlDependency("a", "1", c(href = "http://cdn.example/lib")), TRUE),
    ns_slashslash = call_dep(htmlDependency("a", "1", "//cdn.example/lib"), TRUE),
    ns_multi = call_dep(htmlDependency("a", "1", c(href = "http://x", file = "/tmp")), TRUE),
    ns_na = call_dep(htmlDependency("a", "1", NA_character_), TRUE),
    ns_missing = call_dep(htmlDependency(), TRUE),
    ns_missing_src = call_dep(htmlDependency("a", "1"), TRUE),
    ns_missing_ver = call_dep(htmlDependency("a", src = "p"), TRUE),
    ns_abs_bad_name = call_dep(htmlDependency("", "1", "/tmp"), TRUE),
    ns_abs_missing_ver = call_dep(htmlDependency("a", src = "/tmp"), TRUE),
    bulk = lapply(0:499, function(i) {
      htmlDependency(
        sprintf("lib%d", i),
        sprintf("1.%d.0", i),
        c(href = sprintf("shared/lib%d", i)),
        script = sprintf("lib%d.min.js", i),
        stylesheet = if (i %% 2L == 0L) "x.css" else NULL,
        all_files = (i %% 3L) != 0L
      )
    })
  )
}

encode_one <- function(raw) {
  out <- list()
  for (nm in names(raw)) {
    item <- raw[[nm]]
    if (identical(nm, "bulk")) {
      out[[nm]] <- lapply(item, encode)
    } else {
      out[[nm]] <- encode_run(item)
    }
  }
  out
}

raw <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- encode_one(raw)
payload <- toJSON(
  list(median_ms = median(elapsed) * 1000, value = value),
  auto_unbox = TRUE,
  null = "null",
  na = "null",
  digits = NA
)
cat(payload)
cat("\n")
