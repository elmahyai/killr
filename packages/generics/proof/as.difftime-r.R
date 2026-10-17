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
  as.difftime.mod <- function(tim, ..., w = 1) {
    mean(abs(as.numeric(unclass(tim)))) * w
  }
  as.difftime.sub <- function(tim, ...) 100
  as.difftime.sq <- function(tim, ...) {
    sqrt(mean(as.numeric(unclass(tim))^2))
  }
  as.difftime.child <- function(tim, ...) {
    as.numeric(unclass(tim))[1] + NextMethod()
  }
  as.difftime.parent <- function(tim, ...) sum(as.numeric(unclass(tim)))
  as.difftime.double <- function(tim, ...) {
    if (missing(tim)) -8 else sum(as.numeric(tim)) + 1
  }
  as.difftime.integer <- function(tim, ...) sum(as.numeric(tim)) - 1
  as.difftime.numeric <- function(tim, ...) {
    if (missing(tim)) -9 else sum(as.numeric(tim))
  }
  as.difftime.array <- function(tim, ...) sum(as.numeric(tim)) + 0.25
  as.difftime.AccP <- function(tim, ...) tim@x * 2
  as.difftime.default <- function(tim, ...) -1
  as.difftime.NULL <- function(tim, ...) if (missing(tim)) -2 else -3
  as.difftime.name <- function(tim, ...) if (missing(tim)) -7 else -6
  as.difftime.strict <- function(tim) tim
  as.difftime.only <- function(tim, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    as.difftime(mod),
    as.difftime(mod, w = 2),
    as.difftime(mod, 2),
    as.difftime(ti = mod, w = 4),
    as.difftime(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    as.difftime(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    as.difftime(structure(c(3, 4), class = c("nope", "sq"))),
    as.difftime(structure(c(1.5, 2.5), class = c("child", "parent"))),
    as.difftime(c(1.5, 2.5)),
    as.difftime(1:3),
    as.difftime(matrix(1:4, nrow = 2)),
    as.difftime(matrix(c(1.5, 2.5), nrow = 1)),
    as.difftime(array(c(1.5, 2.5), c(1, 1, 2))),
    as.difftime(new("AccC", x = 1.25)),
    as.difftime(structure(9, class = "unknown")),
    as.difftime(NULL),
    as.difftime(),
    as.difftime(z = 1.5),
    as.difftime(1, tim = c(1.5, 2.5)),
    as.difftime(timm = 1),
    as.difftime(ti = c(1.5, 2.5)),
    as.difftime(ti = 1, tim = c(1.5, 2.5)),
    as.difftime(as.name("x"))
  )

  rm(as.difftime.double, as.difftime.integer, as.difftime.array)
  nums <- c(
    nums,
    as.difftime(c(1.5, 2.5)),
    as.difftime(1:3),
    as.difftime(matrix(c(1.5, 2.5), nrow = 1)),
    as.difftime(array(c(1.5, 2.5), c(1, 1, 2))),
    as.difftime(z = 1.5),
    as.difftime(tim = , z = 1.5)
  )

  rm(as.difftime.numeric, as.difftime.default, as.difftime.NULL, as.difftime.AccP, as.difftime.name)
  errs <- c(
    err(as.difftime(c(1.5, 2.5))),
    err(as.difftime(1:3)),
    err(as.difftime(matrix(1:4, nrow = 2))),
    err(as.difftime(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(as.difftime(TRUE)),
    err(as.difftime("ab")),
    err(as.difftime(NULL)),
    err(as.difftime()),
    err(as.difftime(z = 1.5)),
    err(as.difftime(z = "ab")),
    err(as.difftime(structure(1, class = c("aa", "bb")))),
    err(as.difftime(structure(1, class = ""))),
    err(as.difftime(structure(1, class = "a'b"))),
    err(as.difftime(structure(1, class = c("a'b", "c")))),
    err(as.difftime(new("AccC", x = 1))),
    err(as.difftime(list(1))),
    err(as.difftime(1 + 2i)),
    err(as.difftime(mean)),
    err(as.difftime(tim = )),
    err(as.difftime(t = 1, ti = 2)),
    err(as.difftime(structure(1, class = "strict"), 2)),
    err(as.difftime(structure(1, class = "strict"), 2, z = 3)),
    err(as.difftime(structure(1, class = "strict"), w = 4)),
    err(as.difftime(structure(1, class = c("only", "other"))))
  )
  as.difftime.default <- function(tim, ...) force(tim)
  errs <- c(errs, err(as.difftime()))

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
as.difftime.demo <- function(tim, ...) {
  c(n = length(tim), total = sum(as.numeric(unclass(tim))))
}
msg <- tryCatch(as.difftime(1:3), error = function(e) conditionMessage(e))
hit <- as.difftime(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "as.difftime-r.txt")
)
