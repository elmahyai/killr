.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rlang))
if (as.character(packageVersion("rlang")) != "1.3.0") {
  stop("expected rlang 1.3.0")
}
one <- function() {
  paste(
    as.character(
      c(
        is_call(quote(foo(bar)), "foo"),
        is_call(quote(foo(bar)), "bar"),
        is_call(quote(foo(bar)), quote(foo)),
        is_call(quote(foo(bar)), "foo", n = 1),
        is_call(quote(foo(bar)), "foo", n = 2),
        is_call(quote(+3), n = 1),
        is_call(quote(3 + 3), n = 2),
        is_call(1),
        is_call(NULL),
        is_call(quote(foo()), quote(foo)),
        is_call(quote(foo()), quote(bar)),
        is_call(quote(foo::bar), c("fn", "fn2")),
        is_call(quote(foo::bar), c("fn", "::")),
        is_call(quote(foo::bar), quote(`::`)),
        is_call(quote(foo::bar), list(quote(`@`), quote(`::`))),
        is_call(quote(foo::bar), list(quote(`@`), quote(`:::`))),
        is_call(quote(foo::bar()), ns = NULL),
        is_call(quote(foo::bar()), ns = ""),
        is_call(quote(foo::bar()), ns = "baz"),
        is_call(quote(foo::bar()), ns = "foo"),
        is_call(quote(foo::bar()), name = "bar", ns = "foo"),
        is_call(quote(foo::bar()), name = "baz", ns = "foo"),
        is_call(quote(foo::quux()), ns = c("foo", "bar")),
        is_call(quote(bar::quux()), ns = c("foo", "bar")),
        is_call(quote(baz::quux()), ns = c("foo", "bar")),
        is_call(quote(quux()), ns = c("foo", "bar")),
        is_call(quote(baz::quux()), ns = c("foo", "bar", "")),
        is_call(quote(quux()), ns = c("foo", "bar", "")),
        is_call(quote(base::list()), "list"),
        is_call(quote(base::list()), "list", ns = ""),
        is_call(quote(base::list()), "list", ns = "utils"),
        is_call(quote(base::list()), "list", ns = "base"),
        is_call(quote(base::list()), "list", ns = c("utils", "base")),
        is_call(quote(list()), "list", ns = "base"),
        is_call(quote(list()), "list", ns = c("base", "")),
        is_call(quote(base::list()), "list", ns = c("base", ""))
      )
    ),
    collapse = ","
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- enc2utf8(paste(as.character(value), collapse = "|"))
shown <- gsub("\n", " / ", shown, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
