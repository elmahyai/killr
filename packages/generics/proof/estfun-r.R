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
  estfun.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  estfun.sub <- function(x, ...) 100
  estfun.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  estfun.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  estfun.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  estfun.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  estfun.integer <- function(x, ...) sum(as.numeric(x)) - 1
  estfun.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  estfun.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  estfun.AccP <- function(x, ...) x@x * 2
  estfun.default <- function(x, ...) -1
  estfun.NULL <- function(x, ...) if (missing(x)) -2 else -3
  estfun.name <- function(x, ...) if (missing(x)) -7 else -6
  estfun.strict <- function(x) x
  estfun.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    estfun(mod),
    estfun(mod, w = 2),
    estfun(mod, 2),
    estfun(x = mod, w = 4),
    estfun(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    estfun(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    estfun(structure(c(3, 4), class = c("nope", "sq"))),
    estfun(structure(c(1.5, 2.5), class = c("child", "parent"))),
    estfun(c(1.5, 2.5)),
    estfun(1:3),
    estfun(matrix(1:4, nrow = 2)),
    estfun(matrix(c(1.5, 2.5), nrow = 1)),
    estfun(array(c(1.5, 2.5), c(1, 1, 2))),
    estfun(new("AccC", x = 1.25)),
    estfun(structure(9, class = "unknown")),
    estfun(NULL),
    estfun(),
    estfun(z = 1.5),
    estfun(1, x = c(1.5, 2.5)),
    estfun(xx = 1),
    estfun(x = c(1.5, 2.5)),
    estfun(as.name("x"))
  )

  rm(estfun.double, estfun.integer, estfun.array)
  nums <- c(
    nums,
    estfun(c(1.5, 2.5)),
    estfun(1:3),
    estfun(matrix(c(1.5, 2.5), nrow = 1)),
    estfun(array(c(1.5, 2.5), c(1, 1, 2))),
    estfun(z = 1.5),
    estfun(x = , z = 1.5)
  )

  rm(estfun.numeric, estfun.default, estfun.NULL, estfun.AccP, estfun.name)
  errs <- c(
    err(estfun(c(1.5, 2.5))),
    err(estfun(1:3)),
    err(estfun(matrix(1:4, nrow = 2))),
    err(estfun(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(estfun(TRUE)),
    err(estfun("ab")),
    err(estfun(NULL)),
    err(estfun()),
    err(estfun(z = 1.5)),
    err(estfun(z = "ab")),
    err(estfun(structure(1, class = c("aa", "bb")))),
    err(estfun(structure(1, class = ""))),
    err(estfun(structure(1, class = "a'b"))),
    err(estfun(structure(1, class = c("a'b", "c")))),
    err(estfun(new("AccC", x = 1))),
    err(estfun(list(1))),
    err(estfun(1 + 2i)),
    err(estfun(mean)),
    err(estfun(x = )),
    err(estfun(x = 1, x = 2)),
    err(estfun(structure(1, class = "strict"), 2)),
    err(estfun(structure(1, class = "strict"), 2, z = 3)),
    err(estfun(structure(1, class = "strict"), w = 4)),
    err(estfun(structure(1, class = c("only", "other"))))
  )
  estfun.default <- function(x, ...) force(x)
  errs <- c(errs, err(estfun()))

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
estfun.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(estfun(1:3), error = function(e) conditionMessage(e))
hit <- estfun(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "estfun-r.txt")
)
