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
  interpolate.mod <- function(object, ..., w = 1) {
    mean(abs(as.numeric(unclass(object)))) * w
  }
  interpolate.sub <- function(object, ...) 100
  interpolate.sq <- function(object, ...) {
    sqrt(mean(as.numeric(unclass(object))^2))
  }
  interpolate.child <- function(object, ...) {
    as.numeric(unclass(object))[1] + NextMethod()
  }
  interpolate.parent <- function(object, ...) sum(as.numeric(unclass(object)))
  interpolate.double <- function(object, ...) {
    if (missing(object)) -8 else sum(as.numeric(object)) + 1
  }
  interpolate.integer <- function(object, ...) sum(as.numeric(object)) - 1
  interpolate.numeric <- function(object, ...) {
    if (missing(object)) -9 else sum(as.numeric(object))
  }
  interpolate.array <- function(object, ...) sum(as.numeric(object)) + 0.25
  interpolate.AccP <- function(object, ...) object@x * 2
  interpolate.default <- function(object, ...) -1
  interpolate.NULL <- function(object, ...) if (missing(object)) -2 else -3
  interpolate.name <- function(object, ...) if (missing(object)) -7 else -6
  interpolate.strict <- function(object) object
  interpolate.only <- function(object, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    interpolate(mod),
    interpolate(mod, w = 2),
    interpolate(mod, 2),
    interpolate(obj = mod, w = 4),
    interpolate(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    interpolate(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    interpolate(structure(c(3, 4), class = c("nope", "sq"))),
    interpolate(structure(c(1.5, 2.5), class = c("child", "parent"))),
    interpolate(c(1.5, 2.5)),
    interpolate(1:3),
    interpolate(matrix(1:4, nrow = 2)),
    interpolate(matrix(c(1.5, 2.5), nrow = 1)),
    interpolate(array(c(1.5, 2.5), c(1, 1, 2))),
    interpolate(new("AccC", x = 1.25)),
    interpolate(structure(9, class = "unknown")),
    interpolate(NULL),
    interpolate(),
    interpolate(z = 1.5),
    interpolate(1, object = c(1.5, 2.5)),
    interpolate(objectt = 1),
    interpolate(obj = c(1.5, 2.5)),
    interpolate(obj = 1, object = c(1.5, 2.5)),
    interpolate(as.name("x"))
  )

  rm(interpolate.double, interpolate.integer, interpolate.array)
  nums <- c(
    nums,
    interpolate(c(1.5, 2.5)),
    interpolate(1:3),
    interpolate(matrix(c(1.5, 2.5), nrow = 1)),
    interpolate(array(c(1.5, 2.5), c(1, 1, 2))),
    interpolate(z = 1.5),
    interpolate(object = , z = 1.5)
  )

  rm(interpolate.numeric, interpolate.default, interpolate.NULL, interpolate.AccP, interpolate.name)
  errs <- c(
    err(interpolate(c(1.5, 2.5))),
    err(interpolate(1:3)),
    err(interpolate(matrix(1:4, nrow = 2))),
    err(interpolate(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(interpolate(TRUE)),
    err(interpolate("ab")),
    err(interpolate(NULL)),
    err(interpolate()),
    err(interpolate(z = 1.5)),
    err(interpolate(z = "ab")),
    err(interpolate(structure(1, class = c("aa", "bb")))),
    err(interpolate(structure(1, class = ""))),
    err(interpolate(structure(1, class = "a'b"))),
    err(interpolate(structure(1, class = c("a'b", "c")))),
    err(interpolate(new("AccC", x = 1))),
    err(interpolate(list(1))),
    err(interpolate(1 + 2i)),
    err(interpolate(mean)),
    err(interpolate(object = )),
    err(interpolate(o = 1, ob = 2)),
    err(interpolate(structure(1, class = "strict"), 2)),
    err(interpolate(structure(1, class = "strict"), 2, z = 3)),
    err(interpolate(structure(1, class = "strict"), w = 4)),
    err(interpolate(structure(1, class = c("only", "other"))))
  )
  interpolate.default <- function(object, ...) force(object)
  errs <- c(errs, err(interpolate()))

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
interpolate.demo <- function(object, ...) {
  c(n = length(object), total = sum(as.numeric(unclass(object))))
}
msg <- tryCatch(interpolate(1:3), error = function(e) conditionMessage(e))
hit <- interpolate(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "interpolate-r.txt")
)
