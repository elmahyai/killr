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
  generate.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  generate.sub <- function(x, ...) 100
  generate.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  generate.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  generate.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  generate.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  generate.integer <- function(x, ...) sum(as.numeric(x)) - 1
  generate.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  generate.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  generate.AccP <- function(x, ...) x@x * 2
  generate.default <- function(x, ...) -1
  generate.NULL <- function(x, ...) if (missing(x)) -2 else -3
  generate.name <- function(x, ...) if (missing(x)) -7 else -6
  generate.strict <- function(x) x
  generate.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    generate(mod),
    generate(mod, w = 2),
    generate(mod, 2),
    generate(x = mod, w = 4),
    generate(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    generate(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    generate(structure(c(3, 4), class = c("nope", "sq"))),
    generate(structure(c(1.5, 2.5), class = c("child", "parent"))),
    generate(c(1.5, 2.5)),
    generate(1:3),
    generate(matrix(1:4, nrow = 2)),
    generate(matrix(c(1.5, 2.5), nrow = 1)),
    generate(array(c(1.5, 2.5), c(1, 1, 2))),
    generate(new("AccC", x = 1.25)),
    generate(structure(9, class = "unknown")),
    generate(NULL),
    generate(),
    generate(z = 1.5),
    generate(1, x = c(1.5, 2.5)),
    generate(xx = 1),
    generate(x = c(1.5, 2.5)),
    generate(as.name("x"))
  )

  rm(generate.double, generate.integer, generate.array)
  nums <- c(
    nums,
    generate(c(1.5, 2.5)),
    generate(1:3),
    generate(matrix(c(1.5, 2.5), nrow = 1)),
    generate(array(c(1.5, 2.5), c(1, 1, 2))),
    generate(z = 1.5),
    generate(x = , z = 1.5)
  )

  rm(generate.numeric, generate.default, generate.NULL, generate.AccP, generate.name)
  errs <- c(
    err(generate(c(1.5, 2.5))),
    err(generate(1:3)),
    err(generate(matrix(1:4, nrow = 2))),
    err(generate(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(generate(TRUE)),
    err(generate("ab")),
    err(generate(NULL)),
    err(generate()),
    err(generate(z = 1.5)),
    err(generate(z = "ab")),
    err(generate(structure(1, class = c("aa", "bb")))),
    err(generate(structure(1, class = ""))),
    err(generate(structure(1, class = "a'b"))),
    err(generate(structure(1, class = c("a'b", "c")))),
    err(generate(new("AccC", x = 1))),
    err(generate(list(1))),
    err(generate(1 + 2i)),
    err(generate(mean)),
    err(generate(x = )),
    err(generate(x = 1, x = 2)),
    err(generate(structure(1, class = "strict"), 2)),
    err(generate(structure(1, class = "strict"), 2, z = 3)),
    err(generate(structure(1, class = "strict"), w = 4)),
    err(generate(structure(1, class = c("only", "other"))))
  )
  generate.default <- function(x, ...) force(x)
  errs <- c(errs, err(generate()))

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
generate.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(generate(1:3), error = function(e) conditionMessage(e))
hit <- generate(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "generate-r.txt")
)
