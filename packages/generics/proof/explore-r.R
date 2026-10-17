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
  explore.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  explore.sub <- function(x, ...) 100
  explore.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  explore.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  explore.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  explore.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  explore.integer <- function(x, ...) sum(as.numeric(x)) - 1
  explore.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  explore.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  explore.AccP <- function(x, ...) x@x * 2
  explore.default <- function(x, ...) -1
  explore.NULL <- function(x, ...) if (missing(x)) -2 else -3
  explore.name <- function(x, ...) if (missing(x)) -7 else -6
  explore.strict <- function(x) x
  explore.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    explore(mod),
    explore(mod, w = 2),
    explore(mod, 2),
    explore(x = mod, w = 4),
    explore(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    explore(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    explore(structure(c(3, 4), class = c("nope", "sq"))),
    explore(structure(c(1.5, 2.5), class = c("child", "parent"))),
    explore(c(1.5, 2.5)),
    explore(1:3),
    explore(matrix(1:4, nrow = 2)),
    explore(matrix(c(1.5, 2.5), nrow = 1)),
    explore(array(c(1.5, 2.5), c(1, 1, 2))),
    explore(new("AccC", x = 1.25)),
    explore(structure(9, class = "unknown")),
    explore(NULL),
    explore(),
    explore(z = 1.5),
    explore(1, x = c(1.5, 2.5)),
    explore(xx = 1),
    explore(x = c(1.5, 2.5)),
    explore(as.name("x"))
  )

  rm(explore.double, explore.integer, explore.array)
  nums <- c(
    nums,
    explore(c(1.5, 2.5)),
    explore(1:3),
    explore(matrix(c(1.5, 2.5), nrow = 1)),
    explore(array(c(1.5, 2.5), c(1, 1, 2))),
    explore(z = 1.5),
    explore(x = , z = 1.5)
  )

  rm(explore.numeric, explore.default, explore.NULL, explore.AccP, explore.name)
  errs <- c(
    err(explore(c(1.5, 2.5))),
    err(explore(1:3)),
    err(explore(matrix(1:4, nrow = 2))),
    err(explore(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(explore(TRUE)),
    err(explore("ab")),
    err(explore(NULL)),
    err(explore()),
    err(explore(z = 1.5)),
    err(explore(z = "ab")),
    err(explore(structure(1, class = c("aa", "bb")))),
    err(explore(structure(1, class = ""))),
    err(explore(structure(1, class = "a'b"))),
    err(explore(structure(1, class = c("a'b", "c")))),
    err(explore(new("AccC", x = 1))),
    err(explore(list(1))),
    err(explore(1 + 2i)),
    err(explore(mean)),
    err(explore(x = )),
    err(explore(x = 1, x = 2)),
    err(explore(structure(1, class = "strict"), 2)),
    err(explore(structure(1, class = "strict"), 2, z = 3)),
    err(explore(structure(1, class = "strict"), w = 4)),
    err(explore(structure(1, class = c("only", "other"))))
  )
  explore.default <- function(x, ...) force(x)
  errs <- c(errs, err(explore()))

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
explore.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(explore(1:3), error = function(e) conditionMessage(e))
hit <- explore(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "explore-r.txt")
)
