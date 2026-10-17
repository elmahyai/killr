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
  augment.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  augment.sub <- function(x, ...) 100
  augment.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  augment.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  augment.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  augment.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  augment.integer <- function(x, ...) sum(as.numeric(x)) - 1
  augment.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  augment.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  augment.AccP <- function(x, ...) x@x * 2
  augment.default <- function(x, ...) -1
  augment.NULL <- function(x, ...) if (missing(x)) -2 else -3
  augment.name <- function(x, ...) if (missing(x)) -7 else -6
  augment.strict <- function(x) x
  augment.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    augment(mod),
    augment(mod, w = 2),
    augment(mod, 2),
    augment(x = mod, w = 4),
    augment(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    augment(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    augment(structure(c(3, 4), class = c("nope", "sq"))),
    augment(structure(c(1.5, 2.5), class = c("child", "parent"))),
    augment(c(1.5, 2.5)),
    augment(1:3),
    augment(matrix(1:4, nrow = 2)),
    augment(matrix(c(1.5, 2.5), nrow = 1)),
    augment(array(c(1.5, 2.5), c(1, 1, 2))),
    augment(new("AccC", x = 1.25)),
    augment(structure(9, class = "unknown")),
    augment(NULL),
    augment(),
    augment(z = 1.5),
    augment(1, x = c(1.5, 2.5)),
    augment(xx = 1),
    augment(x = c(1.5, 2.5)),
    augment(as.name("x"))
  )

  rm(augment.double, augment.integer, augment.array)
  nums <- c(
    nums,
    augment(c(1.5, 2.5)),
    augment(1:3),
    augment(matrix(c(1.5, 2.5), nrow = 1)),
    augment(array(c(1.5, 2.5), c(1, 1, 2))),
    augment(z = 1.5),
    augment(x = , z = 1.5)
  )

  rm(augment.numeric, augment.default, augment.NULL, augment.AccP, augment.name)
  errs <- c(
    err(augment(c(1.5, 2.5))),
    err(augment(1:3)),
    err(augment(matrix(1:4, nrow = 2))),
    err(augment(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(augment(TRUE)),
    err(augment("ab")),
    err(augment(NULL)),
    err(augment()),
    err(augment(z = 1.5)),
    err(augment(z = "ab")),
    err(augment(structure(1, class = c("aa", "bb")))),
    err(augment(structure(1, class = ""))),
    err(augment(structure(1, class = "a'b"))),
    err(augment(structure(1, class = c("a'b", "c")))),
    err(augment(new("AccC", x = 1))),
    err(augment(list(1))),
    err(augment(1 + 2i)),
    err(augment(mean)),
    err(augment(x = )),
    err(augment(x = 1, x = 2)),
    err(augment(structure(1, class = "strict"), 2)),
    err(augment(structure(1, class = "strict"), 2, z = 3)),
    err(augment(structure(1, class = "strict"), w = 4)),
    err(augment(structure(1, class = c("only", "other"))))
  )
  augment.default <- function(x, ...) force(x)
  errs <- c(errs, err(augment()))

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
augment.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(augment(1:3), error = function(e) conditionMessage(e))
hit <- augment(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "augment-r.txt")
)
