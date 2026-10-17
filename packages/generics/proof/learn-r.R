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
  learn.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  learn.sub <- function(x, ...) 100
  learn.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  learn.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  learn.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  learn.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  learn.integer <- function(x, ...) sum(as.numeric(x)) - 1
  learn.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  learn.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  learn.AccP <- function(x, ...) x@x * 2
  learn.default <- function(x, ...) -1
  learn.NULL <- function(x, ...) if (missing(x)) -2 else -3
  learn.name <- function(x, ...) if (missing(x)) -7 else -6
  learn.strict <- function(x) x
  learn.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    learn(mod),
    learn(mod, w = 2),
    learn(mod, 2),
    learn(x = mod, w = 4),
    learn(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    learn(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    learn(structure(c(3, 4), class = c("nope", "sq"))),
    learn(structure(c(1.5, 2.5), class = c("child", "parent"))),
    learn(c(1.5, 2.5)),
    learn(1:3),
    learn(matrix(1:4, nrow = 2)),
    learn(matrix(c(1.5, 2.5), nrow = 1)),
    learn(array(c(1.5, 2.5), c(1, 1, 2))),
    learn(new("AccC", x = 1.25)),
    learn(structure(9, class = "unknown")),
    learn(NULL),
    learn(),
    learn(z = 1.5),
    learn(1, x = c(1.5, 2.5)),
    learn(xx = 1),
    learn(x = c(1.5, 2.5)),
    learn(as.name("x"))
  )

  rm(learn.double, learn.integer, learn.array)
  nums <- c(
    nums,
    learn(c(1.5, 2.5)),
    learn(1:3),
    learn(matrix(c(1.5, 2.5), nrow = 1)),
    learn(array(c(1.5, 2.5), c(1, 1, 2))),
    learn(z = 1.5),
    learn(x = , z = 1.5)
  )

  rm(learn.numeric, learn.default, learn.NULL, learn.AccP, learn.name)
  errs <- c(
    err(learn(c(1.5, 2.5))),
    err(learn(1:3)),
    err(learn(matrix(1:4, nrow = 2))),
    err(learn(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(learn(TRUE)),
    err(learn("ab")),
    err(learn(NULL)),
    err(learn()),
    err(learn(z = 1.5)),
    err(learn(z = "ab")),
    err(learn(structure(1, class = c("aa", "bb")))),
    err(learn(structure(1, class = ""))),
    err(learn(structure(1, class = "a'b"))),
    err(learn(structure(1, class = c("a'b", "c")))),
    err(learn(new("AccC", x = 1))),
    err(learn(list(1))),
    err(learn(1 + 2i)),
    err(learn(mean)),
    err(learn(x = )),
    err(learn(x = 1, x = 2)),
    err(learn(structure(1, class = "strict"), 2)),
    err(learn(structure(1, class = "strict"), 2, z = 3)),
    err(learn(structure(1, class = "strict"), w = 4)),
    err(learn(structure(1, class = c("only", "other"))))
  )
  learn.default <- function(x, ...) force(x)
  errs <- c(errs, err(learn()))

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
learn.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(learn(1:3), error = function(e) conditionMessage(e))
hit <- learn(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "learn-r.txt")
)
