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
  components.mod <- function(object, ..., w = 1) {
    mean(abs(as.numeric(unclass(object)))) * w
  }
  components.sub <- function(object, ...) 100
  components.sq <- function(object, ...) {
    sqrt(mean(as.numeric(unclass(object))^2))
  }
  components.child <- function(object, ...) {
    as.numeric(unclass(object))[1] + NextMethod()
  }
  components.parent <- function(object, ...) sum(as.numeric(unclass(object)))
  components.double <- function(object, ...) {
    if (missing(object)) -8 else sum(as.numeric(object)) + 1
  }
  components.integer <- function(object, ...) sum(as.numeric(object)) - 1
  components.numeric <- function(object, ...) {
    if (missing(object)) -9 else sum(as.numeric(object))
  }
  components.array <- function(object, ...) sum(as.numeric(object)) + 0.25
  components.AccP <- function(object, ...) object@x * 2
  components.default <- function(object, ...) -1
  components.NULL <- function(object, ...) if (missing(object)) -2 else -3
  components.name <- function(object, ...) if (missing(object)) -7 else -6
  components.strict <- function(object) object
  components.only <- function(object, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    components(mod),
    components(mod, w = 2),
    components(mod, 2),
    components(obj = mod, w = 4),
    components(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    components(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    components(structure(c(3, 4), class = c("nope", "sq"))),
    components(structure(c(1.5, 2.5), class = c("child", "parent"))),
    components(c(1.5, 2.5)),
    components(1:3),
    components(matrix(1:4, nrow = 2)),
    components(matrix(c(1.5, 2.5), nrow = 1)),
    components(array(c(1.5, 2.5), c(1, 1, 2))),
    components(new("AccC", x = 1.25)),
    components(structure(9, class = "unknown")),
    components(NULL),
    components(),
    components(z = 1.5),
    components(1, object = c(1.5, 2.5)),
    components(objectt = 1),
    components(obj = c(1.5, 2.5)),
    components(obj = 1, object = c(1.5, 2.5)),
    components(as.name("x"))
  )

  rm(components.double, components.integer, components.array)
  nums <- c(
    nums,
    components(c(1.5, 2.5)),
    components(1:3),
    components(matrix(c(1.5, 2.5), nrow = 1)),
    components(array(c(1.5, 2.5), c(1, 1, 2))),
    components(z = 1.5),
    components(object = , z = 1.5)
  )

  rm(components.numeric, components.default, components.NULL, components.AccP, components.name)
  errs <- c(
    err(components(c(1.5, 2.5))),
    err(components(1:3)),
    err(components(matrix(1:4, nrow = 2))),
    err(components(array(c(1.5, 2.5), c(1, 1, 2)))),
    err(components(TRUE)),
    err(components("ab")),
    err(components(NULL)),
    err(components()),
    err(components(z = 1.5)),
    err(components(z = "ab")),
    err(components(structure(1, class = c("aa", "bb")))),
    err(components(structure(1, class = ""))),
    err(components(structure(1, class = "a'b"))),
    err(components(structure(1, class = c("a'b", "c")))),
    err(components(new("AccC", x = 1))),
    err(components(list(1))),
    err(components(1 + 2i)),
    err(components(mean)),
    err(components(object = )),
    err(components(o = 1, ob = 2)),
    err(components(structure(1, class = "strict"), 2)),
    err(components(structure(1, class = "strict"), 2, z = 3)),
    err(components(structure(1, class = "strict"), w = 4)),
    err(components(structure(1, class = c("only", "other"))))
  )
  components.default <- function(object, ...) force(object)
  errs <- c(errs, err(components()))

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
components.demo <- function(object, ...) {
  c(n = length(object), total = sum(as.numeric(unclass(object))))
}
msg <- tryCatch(components(1:3), error = function(e) conditionMessage(e))
hit <- components(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "components-r.txt")
)
