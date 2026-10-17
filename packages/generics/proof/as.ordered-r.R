suppressPackageStartupMessages(library(generics))
stopifnot(identical(as.character(packageVersion("generics")), "0.1.4"))
suppressMessages({
  setClass("AccP", slots = c(x = "numeric"))
  setClass("AccC", contains = "AccP")
})

fmt <- function(x) sprintf("%.17g", x)

err <- function(expr) {
  tryCatch(force(expr), error = function(e) conditionMessage(e))
}

one <- function() {
  as.ordered.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  as.ordered.sub <- function(x, ...) 100
  as.ordered.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  as.ordered.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  as.ordered.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  as.ordered.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  as.ordered.integer <- function(x, ...) sum(as.numeric(x)) - 1
  as.ordered.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  as.ordered.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  as.ordered.AccP <- function(x, ...) x@x * 2
  as.ordered.default <- function(x, ...) -1
  as.ordered.NULL <- function(x, ...) if (missing(x)) -2 else -3
  as.ordered.name <- function(x, ...) if (missing(x)) -7 else -6
  as.ordered.strict <- function(x) x
  as.ordered.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    as.ordered(mod),
    as.ordered(mod, w = 2),
    as.ordered(mod, 2),
    as.ordered(x = mod, w = 4),
    as.ordered(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    as.ordered(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    as.ordered(structure(c(3, 4), class = c("nope", "sq"))),
    as.ordered(structure(c(1.5, 2.5), class = c("child", "parent"))),
    as.ordered(c(1.5, 2.5)),
    as.ordered(1:3),
    as.ordered(matrix(1:4, nrow = 2)),
    as.ordered(matrix(c(1.5, 2.5), nrow = 1)),
    as.ordered(array(c(1.5, 2.5), c(1, 1, 2))),
    as.ordered(new("AccC", x = 1.25)),
    as.ordered(structure(9, class = "unknown")),
    as.ordered(NULL),
    as.ordered(),
    as.ordered(z = 1.5),
    as.ordered(1, x = c(1.5, 2.5)),
    as.ordered(xx = 1),
    as.ordered(x = c(1.5, 2.5)),
    as.ordered(as.name("x"))
  )

  rm(as.ordered.double, as.ordered.integer, as.ordered.array)
  nums <- c(
    nums,
    as.ordered(c(1.5, 2.5)),
    as.ordered(1:3),
    as.ordered(matrix(c(1.5, 2.5), nrow = 1)),
    as.ordered(array(c(1.5, 2.5), c(1, 1, 2))),
    as.ordered(z = 1.5),
    as.ordered(x = , z = 1.5)
  )

  rm(as.ordered.numeric, as.ordered.default, as.ordered.NULL, as.ordered.AccP, as.ordered.name)
  errs <- c(
    err(as.ordered(c(1.5, 2.5))),
    err(as.ordered(1:3)),
    err(as.ordered(matrix(1:4, nrow = 2))),
    err(as.ordered(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(as.ordered(TRUE)),
    err(as.ordered("ab")),
    err(as.ordered(NULL)),
    err(as.ordered()),
    err(as.ordered(z = 1.5)),
    err(as.ordered(z = "ab")),
    err(as.ordered(structure(1, class = c("aa", "bb")))),
    err(as.ordered(structure(1, class = ""))),
    err(as.ordered(structure(1, class = "a'b"))),
    err(as.ordered(structure(1, class = c("a'b", "c")))),
    err(as.ordered(new("AccC", x = 1))),
    err(as.ordered(list(1))),
    err(as.ordered(1 + 2i)),
    err(as.ordered(mean)),
    err(as.ordered(x = )),
    err(as.ordered(x = 1, x = 2)),
    err(as.ordered(structure(1, class = "strict"), 2)),
    err(as.ordered(structure(1, class = "strict"), 2, z = 3)),
    err(as.ordered(structure(1, class = "strict"), w = 4)),
    err(as.ordered(structure(1, class = c("only", "other"))))
  )
  as.ordered.default <- function(x, ...) force(x)
  errs <- c(errs, err(as.ordered()))

  paste(c(paste(vapply(nums, fmt, ""), collapse = ","), errs), collapse = " || ")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE ", value, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))

cmd <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", cmd[grep("^--file=", cmd)])
out_dir <- file.path(normalizePath(file.path(dirname(script), "..")), "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
as.ordered.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(as.ordered(1:3), error = function(e) conditionMessage(e))
hit <- as.ordered(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "as.ordered-r.txt")
)
