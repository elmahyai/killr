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
  as.factor.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  as.factor.sub <- function(x, ...) 100
  as.factor.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  as.factor.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  as.factor.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  as.factor.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  as.factor.integer <- function(x, ...) sum(as.numeric(x)) - 1
  as.factor.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  as.factor.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  as.factor.AccP <- function(x, ...) x@x * 2
  as.factor.default <- function(x, ...) -1
  as.factor.NULL <- function(x, ...) if (missing(x)) -2 else -3
  as.factor.name <- function(x, ...) if (missing(x)) -7 else -6
  as.factor.strict <- function(x) x
  as.factor.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    as.factor(mod),
    as.factor(mod, w = 2),
    as.factor(mod, 2),
    as.factor(x = mod, w = 4),
    as.factor(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    as.factor(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    as.factor(structure(c(3, 4), class = c("nope", "sq"))),
    as.factor(structure(c(1.5, 2.5), class = c("child", "parent"))),
    as.factor(c(1.5, 2.5)),
    as.factor(1:3),
    as.factor(matrix(1:4, nrow = 2)),
    as.factor(matrix(c(1.5, 2.5), nrow = 1)),
    as.factor(array(c(1.5, 2.5), c(1, 1, 2))),
    as.factor(new("AccC", x = 1.25)),
    as.factor(structure(9, class = "unknown")),
    as.factor(NULL),
    as.factor(),
    as.factor(z = 1.5),
    as.factor(1, x = c(1.5, 2.5)),
    as.factor(xx = 1),
    as.factor(x = c(1.5, 2.5)),
    as.factor(as.name("x"))
  )

  rm(as.factor.double, as.factor.integer, as.factor.array)
  nums <- c(
    nums,
    as.factor(c(1.5, 2.5)),
    as.factor(1:3),
    as.factor(matrix(c(1.5, 2.5), nrow = 1)),
    as.factor(array(c(1.5, 2.5), c(1, 1, 2))),
    as.factor(z = 1.5),
    as.factor(x = , z = 1.5)
  )

  rm(as.factor.numeric, as.factor.default, as.factor.NULL, as.factor.AccP, as.factor.name)
  errs <- c(
    err(as.factor(c(1.5, 2.5))),
    err(as.factor(1:3)),
    err(as.factor(matrix(1:4, nrow = 2))),
    err(as.factor(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(as.factor(TRUE)),
    err(as.factor("ab")),
    err(as.factor(NULL)),
    err(as.factor()),
    err(as.factor(z = 1.5)),
    err(as.factor(z = "ab")),
    err(as.factor(structure(1, class = c("aa", "bb")))),
    err(as.factor(structure(1, class = ""))),
    err(as.factor(structure(1, class = "a'b"))),
    err(as.factor(structure(1, class = c("a'b", "c")))),
    err(as.factor(new("AccC", x = 1))),
    err(as.factor(list(1))),
    err(as.factor(1 + 2i)),
    err(as.factor(mean)),
    err(as.factor(x = )),
    err(as.factor(x = 1, x = 2)),
    err(as.factor(structure(1, class = "strict"), 2)),
    err(as.factor(structure(1, class = "strict"), 2, z = 3)),
    err(as.factor(structure(1, class = "strict"), w = 4)),
    err(as.factor(structure(1, class = c("only", "other"))))
  )
  as.factor.default <- function(x, ...) force(x)
  errs <- c(errs, err(as.factor()))

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
as.factor.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(as.factor(1:3), error = function(e) conditionMessage(e))
hit <- as.factor(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "as.factor-r.txt")
)
