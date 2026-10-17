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
  glance.mod <- function(x, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  glance.sub <- function(x, ...) 100
  glance.sq <- function(x, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  glance.child <- function(x, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  glance.parent <- function(x, ...) sum(as.numeric(unclass(x)))
  glance.double <- function(x, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  glance.integer <- function(x, ...) sum(as.numeric(x)) - 1
  glance.numeric <- function(x, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  glance.array <- function(x, ...) sum(as.numeric(x)) + 0.25
  glance.AccP <- function(x, ...) x@x * 2
  glance.default <- function(x, ...) -1
  glance.NULL <- function(x, ...) if (missing(x)) -2 else -3
  glance.name <- function(x, ...) if (missing(x)) -7 else -6
  glance.strict <- function(x) x
  glance.only <- function(x, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    glance(mod),
    glance(mod, w = 2),
    glance(mod, 2),
    glance(x = mod, w = 4),
    glance(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    glance(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    glance(structure(c(3, 4), class = c("nope", "sq"))),
    glance(structure(c(1.5, 2.5), class = c("child", "parent"))),
    glance(c(1.5, 2.5)),
    glance(1:3),
    glance(matrix(1:4, nrow = 2)),
    glance(matrix(c(1.5, 2.5), nrow = 1)),
    glance(array(c(1.5, 2.5), c(1, 1, 2))),
    glance(new("AccC", x = 1.25)),
    glance(structure(9, class = "unknown")),
    glance(NULL),
    glance(),
    glance(z = 1.5),
    glance(1, x = c(1.5, 2.5)),
    glance(xx = 1),
    glance(x = c(1.5, 2.5)),
    glance(as.name("x"))
  )

  rm(glance.double, glance.integer, glance.array)
  nums <- c(
    nums,
    glance(c(1.5, 2.5)),
    glance(1:3),
    glance(matrix(c(1.5, 2.5), nrow = 1)),
    glance(array(c(1.5, 2.5), c(1, 1, 2))),
    glance(z = 1.5),
    glance(x = , z = 1.5)
  )

  rm(glance.numeric, glance.default, glance.NULL, glance.AccP, glance.name)
  errs <- c(
    err(glance(c(1.5, 2.5))),
    err(glance(1:3)),
    err(glance(matrix(1:4, nrow = 2))),
    err(glance(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(glance(TRUE)),
    err(glance("ab")),
    err(glance(NULL)),
    err(glance()),
    err(glance(z = 1.5)),
    err(glance(z = "ab")),
    err(glance(structure(1, class = c("aa", "bb")))),
    err(glance(structure(1, class = ""))),
    err(glance(structure(1, class = "a'b"))),
    err(glance(structure(1, class = c("a'b", "c")))),
    err(glance(new("AccC", x = 1))),
    err(glance(list(1))),
    err(glance(1 + 2i)),
    err(glance(mean)),
    err(glance(x = )),
    err(glance(x = 1, x = 2)),
    err(glance(structure(1, class = "strict"), 2)),
    err(glance(structure(1, class = "strict"), 2, z = 3)),
    err(glance(structure(1, class = "strict"), w = 4)),
    err(glance(structure(1, class = c("only", "other"))))
  )
  glance.default <- function(x, ...) force(x)
  errs <- c(errs, err(glance()))

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
glance.demo <- function(x, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(glance(1:3), error = function(e) conditionMessage(e))
hit <- glance(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "glance-r.txt")
)
