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
  compile.mod <- function(object, ..., w = 1) {
    mean(abs(as.numeric(unclass(object)))) * w
  }
  compile.sub <- function(object, ...) 100
  compile.sq <- function(object, ...) {
    sqrt(mean(as.numeric(unclass(object))^2))
  }
  compile.child <- function(object, ...) {
    as.numeric(unclass(object))[1] + NextMethod()
  }
  compile.parent <- function(object, ...) sum(as.numeric(unclass(object)))
  compile.double <- function(object, ...) {
    if (missing(object)) -8 else sum(as.numeric(object)) + 1
  }
  compile.integer <- function(object, ...) sum(as.numeric(object)) - 1
  compile.numeric <- function(object, ...) {
    if (missing(object)) -9 else sum(as.numeric(object))
  }
  compile.array <- function(object, ...) sum(as.numeric(object)) + 0.25
  compile.AccP <- function(object, ...) object@x * 2
  compile.default <- function(object, ...) -1
  compile.NULL <- function(object, ...) if (missing(object)) -2 else -3
  compile.name <- function(object, ...) if (missing(object)) -7 else -6
  compile.strict <- function(object) object
  compile.only <- function(object, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    compile(mod),
    compile(mod, w = 2),
    compile(mod, 2),
    compile(obj = mod, w = 4),
    compile(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    compile(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    compile(structure(c(3, 4), class = c("nope", "sq"))),
    compile(structure(c(1.5, 2.5), class = c("child", "parent"))),
    compile(c(1.5, 2.5)),
    compile(1:3),
    compile(matrix(1:4, nrow = 2)),
    compile(matrix(c(1.5, 2.5), nrow = 1)),
    compile(array(c(1.5, 2.5), c(1, 1, 2))),
    compile(new("AccC", x = 1.25)),
    compile(structure(9, class = "unknown")),
    compile(NULL),
    compile(),
    compile(z = 1.5),
    compile(1, object = c(1.5, 2.5)),
    compile(objectt = 1),
    compile(obj = c(1.5, 2.5)),
    compile(obj = 1, object = c(1.5, 2.5)),
    compile(as.name("x"))
  )

  rm(compile.double, compile.integer, compile.array)
  nums <- c(
    nums,
    compile(c(1.5, 2.5)),
    compile(1:3),
    compile(matrix(c(1.5, 2.5), nrow = 1)),
    compile(array(c(1.5, 2.5), c(1, 1, 2))),
    compile(z = 1.5),
    compile(object = , z = 1.5)
  )

  rm(compile.numeric, compile.default, compile.NULL, compile.AccP, compile.name)
  errs <- c(
    err(compile(c(1.5, 2.5))),
    err(compile(1:3)),
    err(compile(matrix(1:4, nrow = 2))),
    err(compile(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(compile(TRUE)),
    err(compile("ab")),
    err(compile(NULL)),
    err(compile()),
    err(compile(z = 1.5)),
    err(compile(z = "ab")),
    err(compile(structure(1, class = c("aa", "bb")))),
    err(compile(structure(1, class = ""))),
    err(compile(structure(1, class = "a'b"))),
    err(compile(structure(1, class = c("a'b", "c")))),
    err(compile(new("AccC", x = 1))),
    err(compile(list(1))),
    err(compile(1 + 2i)),
    err(compile(mean)),
    err(compile(object = )),
    err(compile(o = 1, ob = 2)),
    err(compile(structure(1, class = "strict"), 2)),
    err(compile(structure(1, class = "strict"), 2, z = 3)),
    err(compile(structure(1, class = "strict"), w = 4)),
    err(compile(structure(1, class = c("only", "other"))))
  )
  compile.default <- function(object, ...) force(object)
  errs <- c(errs, err(compile()))

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
compile.demo <- function(object, ...) {
  c(n = length(object), total = sum(as.numeric(unclass(object))))
}
msg <- tryCatch(compile(1:3), error = function(e) conditionMessage(e))
hit <- compile(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "compile-r.txt")
)
