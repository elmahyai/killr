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
  equation.mod <- function(object, ..., w = 1) {
    mean(abs(as.numeric(unclass(object)))) * w
  }
  equation.sub <- function(object, ...) 100
  equation.sq <- function(object, ...) {
    sqrt(mean(as.numeric(unclass(object))^2))
  }
  equation.child <- function(object, ...) {
    as.numeric(unclass(object))[1] + NextMethod()
  }
  equation.parent <- function(object, ...) sum(as.numeric(unclass(object)))
  equation.double <- function(object, ...) {
    if (missing(object)) -8 else sum(as.numeric(object)) + 1
  }
  equation.integer <- function(object, ...) sum(as.numeric(object)) - 1
  equation.numeric <- function(object, ...) {
    if (missing(object)) -9 else sum(as.numeric(object))
  }
  equation.array <- function(object, ...) sum(as.numeric(object)) + 0.25
  equation.AccP <- function(object, ...) object@x * 2
  equation.default <- function(object, ...) -1
  equation.NULL <- function(object, ...) if (missing(object)) -2 else -3
  equation.name <- function(object, ...) if (missing(object)) -7 else -6
  equation.strict <- function(object) object
  equation.only <- function(object, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    equation(mod),
    equation(mod, w = 2),
    equation(mod, 2),
    equation(obj = mod, w = 4),
    equation(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    equation(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    equation(structure(c(3, 4), class = c("nope", "sq"))),
    equation(structure(c(1.5, 2.5), class = c("child", "parent"))),
    equation(c(1.5, 2.5)),
    equation(1:3),
    equation(matrix(1:4, nrow = 2)),
    equation(matrix(c(1.5, 2.5), nrow = 1)),
    equation(array(c(1.5, 2.5), c(1, 1, 2))),
    equation(new("AccC", x = 1.25)),
    equation(structure(9, class = "unknown")),
    equation(NULL),
    equation(),
    equation(z = 1.5),
    equation(1, object = c(1.5, 2.5)),
    equation(objectt = 1),
    equation(obj = c(1.5, 2.5)),
    equation(obj = 1, object = c(1.5, 2.5)),
    equation(as.name("x"))
  )

  rm(equation.double, equation.integer, equation.array)
  nums <- c(
    nums,
    equation(c(1.5, 2.5)),
    equation(1:3),
    equation(matrix(c(1.5, 2.5), nrow = 1)),
    equation(array(c(1.5, 2.5), c(1, 1, 2))),
    equation(z = 1.5),
    equation(object = , z = 1.5)
  )

  rm(equation.numeric, equation.default, equation.NULL, equation.AccP, equation.name)
  errs <- c(
    err(equation(c(1.5, 2.5))),
    err(equation(1:3)),
    err(equation(matrix(1:4, nrow = 2))),
    err(equation(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(equation(TRUE)),
    err(equation("ab")),
    err(equation(NULL)),
    err(equation()),
    err(equation(z = 1.5)),
    err(equation(z = "ab")),
    err(equation(structure(1, class = c("aa", "bb")))),
    err(equation(structure(1, class = ""))),
    err(equation(structure(1, class = "a'b"))),
    err(equation(structure(1, class = c("a'b", "c")))),
    err(equation(new("AccC", x = 1))),
    err(equation(list(1))),
    err(equation(1 + 2i)),
    err(equation(mean)),
    err(equation(object = )),
    err(equation(o = 1, ob = 2)),
    err(equation(structure(1, class = "strict"), 2)),
    err(equation(structure(1, class = "strict"), 2, z = 3)),
    err(equation(structure(1, class = "strict"), w = 4)),
    err(equation(structure(1, class = c("only", "other"))))
  )
  equation.default <- function(object, ...) force(object)
  errs <- c(errs, err(equation()))

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
equation.demo <- function(object, ...) {
  c(n = length(object), total = sum(as.numeric(unclass(object))))
}
msg <- tryCatch(equation(1:3), error = function(e) conditionMessage(e))
hit <- equation(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "equation-r.txt")
)
