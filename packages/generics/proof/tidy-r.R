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
  tidy.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  tidy.sub <- function(x, ...) 100
  tidy.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  tidy.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  tidy.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  tidy.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  tidy.integer <- function(x, ...) sum(as.numeric(x)) - 1
  tidy.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  tidy.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  tidy.AccP <- function(x, ...) x@x * 2
  tidy.default <- function(x, ...) -1
  tidy.NULL <- function(x, ...) if (missing(x)) -2 else -3
  tidy.name <- function(x, ...) if (missing(x)) -7 else -6
  tidy.strict <- function(x) x
  tidy.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    tidy(mod),
    tidy(mod, w = 2),
    tidy(mod, 2),
    tidy(x = mod, w = 4),
    tidy(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    tidy(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    tidy(structure(c(3, 4), class = c("nope", "sq"))),
    tidy(structure(c(1.5, 2.5), class = c("child", "parent"))),
    tidy(c(1.5, 2.5)),
    tidy(1:3),
    tidy(matrix(1:4, nrow = 2)),
    tidy(matrix(c(1.5, 2.5), nrow = 1)),
    tidy(array(c(1.5, 2.5), c(1, 1, 2))),
    tidy(new("AccC", x = 1.25)),
    tidy(structure(9, class = "unknown")),
    tidy(NULL),
    tidy(),
    tidy(z = 1.5),
    tidy(1, x = c(1.5, 2.5)),
    tidy(xx = 1),
    tidy(x = c(1.5, 2.5)),
    tidy(as.name("x"))
  )

  rm(tidy.double, tidy.integer, tidy.array)
  nums <- c(
    nums,
    tidy(c(1.5, 2.5)),
    tidy(1:3),
    tidy(matrix(c(1.5, 2.5), nrow = 1)),
    tidy(array(c(1.5, 2.5), c(1, 1, 2))),
    tidy(z = 1.5),
    tidy(x = , z = 1.5)
  )

  rm(tidy.numeric, tidy.default, tidy.NULL, tidy.AccP, tidy.name)
  errs <- c(
    err(tidy(c(1.5, 2.5))),
    err(tidy(1:3)),
    err(tidy(matrix(1:4, nrow = 2))),
    err(tidy(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(tidy(TRUE)),
    err(tidy("ab")),
    err(tidy(NULL)),
    err(tidy()),
    err(tidy(z = 1.5)),
    err(tidy(z = "ab")),
    err(tidy(structure(1, class = c("aa", "bb")))),
    err(tidy(structure(1, class = ""))),
    err(tidy(structure(1, class = "a'b"))),
    err(tidy(structure(1, class = c("a'b", "c")))),
    err(tidy(new("AccC", x = 1))),
    err(tidy(list(1))),
    err(tidy(1 + 2i)),
    err(tidy(mean)),
    err(tidy(x = )),
    err(tidy(x = 1, x = 2)),
    err(tidy(structure(1, class = "strict"), 2)),
    err(tidy(structure(1, class = "strict"), 2, z = 3)),
    err(tidy(structure(1, class = "strict"), w = 4)),
    err(tidy(structure(1, class = c("only", "other"))))
  )
  tidy.default <- function(x, ...) force(x)
  errs <- c(errs, err(tidy()))

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
tidy.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(tidy(1:3), error = function(e) conditionMessage(e))
hit <- tidy(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "tidy-r.txt")
)
