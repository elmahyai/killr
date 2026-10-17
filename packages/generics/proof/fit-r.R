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
  fit.mod <- function(object, ..., w = 1) {
    mean(abs(as.numeric(unclass(object)))) * w
  }
  fit.sub <- function(object, ...) 100
  fit.sq <- function(object, ...) {
    sqrt(mean(as.numeric(unclass(object))^2))
  }
  fit.child <- function(object, ...) {
    as.numeric(unclass(object))[1] + NextMethod()
  }
  fit.parent <- function(object, ...) sum(as.numeric(unclass(object)))
  fit.double <- function(object, ...) {
    if (missing(object)) -8 else sum(as.numeric(object)) + 1
  }
  fit.integer <- function(object, ...) sum(as.numeric(object)) - 1
  fit.numeric <- function(object, ...) {
    if (missing(object)) -9 else sum(as.numeric(object))
  }
  fit.array <- function(object, ...) sum(as.numeric(object)) + 0.25
  fit.AccP <- function(object, ...) object@x * 2
  fit.default <- function(object, ...) -1
  fit.NULL <- function(object, ...) if (missing(object)) -2 else -3
  fit.name <- function(object, ...) if (missing(object)) -7 else -6
  fit.strict <- function(object) object
  fit.only <- function(object, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    fit(mod),
    fit(mod, w = 2),
    fit(mod, 2),
    fit(obj = mod, w = 4),
    fit(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    fit(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    fit(structure(c(3, 4), class = c("nope", "sq"))),
    fit(structure(c(1.5, 2.5), class = c("child", "parent"))),
    fit(c(1.5, 2.5)),
    fit(1:3),
    fit(matrix(1:4, nrow = 2)),
    fit(matrix(c(1.5, 2.5), nrow = 1)),
    fit(array(c(1.5, 2.5), c(1, 1, 2))),
    fit(new("AccC", x = 1.25)),
    fit(structure(9, class = "unknown")),
    fit(NULL),
    fit(),
    fit(z = 1.5),
    fit(1, object = c(1.5, 2.5)),
    fit(objectt = 1),
    fit(obj = c(1.5, 2.5)),
    fit(obj = 1, object = c(1.5, 2.5)),
    fit(as.name("x"))
  )

  rm(fit.double, fit.integer, fit.array)
  nums <- c(
    nums,
    fit(c(1.5, 2.5)),
    fit(1:3),
    fit(matrix(c(1.5, 2.5), nrow = 1)),
    fit(array(c(1.5, 2.5), c(1, 1, 2))),
    fit(z = 1.5),
    fit(object = , z = 1.5)
  )

  rm(fit.numeric, fit.default, fit.NULL, fit.AccP, fit.name)
  errs <- c(
    err(fit(c(1.5, 2.5))),
    err(fit(1:3)),
    err(fit(matrix(1:4, nrow = 2))),
    err(fit(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(fit(TRUE)),
    err(fit("ab")),
    err(fit(NULL)),
    err(fit()),
    err(fit(z = 1.5)),
    err(fit(z = "ab")),
    err(fit(structure(1, class = c("aa", "bb")))),
    err(fit(structure(1, class = ""))),
    err(fit(structure(1, class = "a'b"))),
    err(fit(structure(1, class = c("a'b", "c")))),
    err(fit(new("AccC", x = 1))),
    err(fit(list(1))),
    err(fit(1 + 2i)),
    err(fit(mean)),
    err(fit(object = )),
    err(fit(o = 1, ob = 2)),
    err(fit(structure(1, class = "strict"), 2)),
    err(fit(structure(1, class = "strict"), 2, z = 3)),
    err(fit(structure(1, class = "strict"), w = 4)),
    err(fit(structure(1, class = c("only", "other"))))
  )
  fit.default <- function(object, ...) force(object)
  errs <- c(errs, err(fit()))

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
fit.demo <- function(object, ...) {
  c(n = length(object), total = sum(as.numeric(unclass(object))))
}
msg <- tryCatch(fit(1:3), error = function(e) conditionMessage(e))
hit <- fit(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "fit-r.txt")
)
