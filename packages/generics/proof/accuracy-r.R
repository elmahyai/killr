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
  accuracy.mod <- function(object, ..., w = 1) {
    mean(abs(as.numeric(unclass(object)))) * w
  }
  accuracy.sub <- function(object, ...) 100
  accuracy.sq <- function(object, ...) {
    sqrt(mean(as.numeric(unclass(object))^2))
  }
  accuracy.child <- function(object, ...) {
    as.numeric(unclass(object))[1] + NextMethod()
  }
  accuracy.parent <- function(object, ...) sum(as.numeric(unclass(object)))
  accuracy.double <- function(object, ...) {
    if (missing(object)) -8 else sum(as.numeric(object)) + 1
  }
  accuracy.integer <- function(object, ...) sum(as.numeric(object)) - 1
  accuracy.numeric <- function(object, ...) {
    if (missing(object)) -9 else sum(as.numeric(object))
  }
  accuracy.array <- function(object, ...) sum(as.numeric(object)) + 0.25
  accuracy.AccP <- function(object, ...) object@x * 2
  accuracy.default <- function(object, ...) -1
  accuracy.NULL <- function(object, ...) if (missing(object)) -2 else -3
  accuracy.name <- function(object, ...) if (missing(object)) -7 else -6
  accuracy.strict <- function(object) object
  accuracy.only <- function(object, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    accuracy(mod),
    accuracy(mod, w = 2),
    accuracy(mod, 2),
    accuracy(obj = mod, w = 4),
    accuracy(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    accuracy(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    accuracy(structure(c(3, 4), class = c("nope", "sq"))),
    accuracy(structure(c(1.5, 2.5), class = c("child", "parent"))),
    accuracy(c(1.5, 2.5)),
    accuracy(1:3),
    accuracy(matrix(1:4, nrow = 2)),
    accuracy(matrix(c(1.5, 2.5), nrow = 1)),
    accuracy(array(c(1.5, 2.5), c(1, 1, 2))),
    accuracy(new("AccC", x = 1.25)),
    accuracy(structure(9, class = "unknown")),
    accuracy(NULL),
    accuracy(),
    accuracy(z = 1.5),
    accuracy(1, object = c(1.5, 2.5)),
    accuracy(objectt = 1),
    accuracy(obj = c(1.5, 2.5)),
    accuracy(obj = 1, object = c(1.5, 2.5)),
    accuracy(as.name("x"))
  )

  rm(accuracy.double, accuracy.integer, accuracy.array)
  nums <- c(
    nums,
    accuracy(c(1.5, 2.5)),
    accuracy(1:3),
    accuracy(matrix(c(1.5, 2.5), nrow = 1)),
    accuracy(array(c(1.5, 2.5), c(1, 1, 2))),
    accuracy(z = 1.5),
    accuracy(object = , z = 1.5)
  )

  rm(accuracy.numeric, accuracy.default, accuracy.NULL, accuracy.AccP, accuracy.name)
  errs <- c(
    err(accuracy(c(1.5, 2.5))),
    err(accuracy(1:3)),
    err(accuracy(matrix(1:4, nrow = 2))),
    err(accuracy(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(accuracy(TRUE)),
    err(accuracy("ab")),
    err(accuracy(NULL)),
    err(accuracy()),
    err(accuracy(z = 1.5)),
    err(accuracy(z = "ab")),
    err(accuracy(structure(1, class = c("aa", "bb")))),
    err(accuracy(structure(1, class = ""))),
    err(accuracy(structure(1, class = "a'b"))),
    err(accuracy(structure(1, class = c("a'b", "c")))),
    err(accuracy(new("AccC", x = 1))),
    err(accuracy(list(1))),
    err(accuracy(1 + 2i)),
    err(accuracy(mean)),
    err(accuracy(object = )),
    err(accuracy(o = 1, ob = 2)),
    err(accuracy(structure(1, class = "strict"), 2)),
    err(accuracy(structure(1, class = "strict"), 2, z = 3)),
    err(accuracy(structure(1, class = "strict"), w = 4)),
    err(accuracy(structure(1, class = c("only", "other"))))
  )
  accuracy.default <- function(object, ...) force(object)
  errs <- c(errs, err(accuracy()))

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
accuracy.demo <- function(object, ...) {
  c(n = length(object), total = sum(as.numeric(unclass(object))))
}
msg <- tryCatch(accuracy(1:3), error = function(e) conditionMessage(e))
hit <- accuracy(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "accuracy-r.txt")
)
