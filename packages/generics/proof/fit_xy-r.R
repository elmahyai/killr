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
  fit_xy.mod <- function(object, ..., w = 1) {
    mean(abs(as.numeric(unclass(object)))) * w
  }
  fit_xy.sub <- function(object, ...) 100
  fit_xy.sq <- function(object, ...) {
    sqrt(mean(as.numeric(unclass(object))^2))
  }
  fit_xy.child <- function(object, ...) {
    as.numeric(unclass(object))[1] + NextMethod()
  }
  fit_xy.parent <- function(object, ...) sum(as.numeric(unclass(object)))
  fit_xy.double <- function(object, ...) {
    if (missing(object)) -8 else sum(as.numeric(object)) + 1
  }
  fit_xy.integer <- function(object, ...) sum(as.numeric(object)) - 1
  fit_xy.numeric <- function(object, ...) {
    if (missing(object)) -9 else sum(as.numeric(object))
  }
  fit_xy.array <- function(object, ...) sum(as.numeric(object)) + 0.25
  fit_xy.AccP <- function(object, ...) object@x * 2
  fit_xy.default <- function(object, ...) -1
  fit_xy.NULL <- function(object, ...) if (missing(object)) -2 else -3
  fit_xy.name <- function(object, ...) if (missing(object)) -7 else -6
  fit_xy.strict <- function(object) object
  fit_xy.only <- function(object, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    fit_xy(mod),
    fit_xy(mod, w = 2),
    fit_xy(mod, 2),
    fit_xy(obj = mod, w = 4),
    fit_xy(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    fit_xy(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    fit_xy(structure(c(3, 4), class = c("nope", "sq"))),
    fit_xy(structure(c(1.5, 2.5), class = c("child", "parent"))),
    fit_xy(c(1.5, 2.5)),
    fit_xy(1:3),
    fit_xy(matrix(1:4, nrow = 2)),
    fit_xy(matrix(c(1.5, 2.5), nrow = 1)),
    fit_xy(array(c(1.5, 2.5), c(1, 1, 2))),
    fit_xy(new("AccC", x = 1.25)),
    fit_xy(structure(9, class = "unknown")),
    fit_xy(NULL),
    fit_xy(),
    fit_xy(z = 1.5),
    fit_xy(1, object = c(1.5, 2.5)),
    fit_xy(objectt = 1),
    fit_xy(obj = c(1.5, 2.5)),
    fit_xy(obj = 1, object = c(1.5, 2.5)),
    fit_xy(as.name("x"))
  )

  rm(fit_xy.double, fit_xy.integer, fit_xy.array)
  nums <- c(
    nums,
    fit_xy(c(1.5, 2.5)),
    fit_xy(1:3),
    fit_xy(matrix(c(1.5, 2.5), nrow = 1)),
    fit_xy(array(c(1.5, 2.5), c(1, 1, 2))),
    fit_xy(z = 1.5),
    fit_xy(object = , z = 1.5)
  )

  rm(fit_xy.numeric, fit_xy.default, fit_xy.NULL, fit_xy.AccP, fit_xy.name)
  errs <- c(
    err(fit_xy(c(1.5, 2.5))),
    err(fit_xy(1:3)),
    err(fit_xy(matrix(1:4, nrow = 2))),
    err(fit_xy(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(fit_xy(TRUE)),
    err(fit_xy("ab")),
    err(fit_xy(NULL)),
    err(fit_xy()),
    err(fit_xy(z = 1.5)),
    err(fit_xy(z = "ab")),
    err(fit_xy(structure(1, class = c("aa", "bb")))),
    err(fit_xy(structure(1, class = ""))),
    err(fit_xy(structure(1, class = "a'b"))),
    err(fit_xy(structure(1, class = c("a'b", "c")))),
    err(fit_xy(new("AccC", x = 1))),
    err(fit_xy(list(1))),
    err(fit_xy(1 + 2i)),
    err(fit_xy(mean)),
    err(fit_xy(object = )),
    err(fit_xy(o = 1, ob = 2)),
    err(fit_xy(structure(1, class = "strict"), 2)),
    err(fit_xy(structure(1, class = "strict"), 2, z = 3)),
    err(fit_xy(structure(1, class = "strict"), w = 4)),
    err(fit_xy(structure(1, class = c("only", "other"))))
  )
  fit_xy.default <- function(object, ...) force(object)
  errs <- c(errs, err(fit_xy()))

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
fit_xy.demo <- function(object, ...) {
  c(n = length(object), total = sum(as.numeric(unclass(object))))
}
msg <- tryCatch(fit_xy(1:3), error = function(e) conditionMessage(e))
hit <- fit_xy(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "fit_xy-r.txt")
)
