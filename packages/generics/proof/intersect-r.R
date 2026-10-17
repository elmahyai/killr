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
  ns <- asNamespace("generics")
  default_neg <- function(x, y, ...) -1
  dispatch_class <- function(x) {
    if (is.null(x)) {
      return("NULL")
    }
    if (is.matrix(x)) {
      tail <- if (is.integer(x)) c("integer", "numeric") else c("double", "numeric")
      return(c("matrix", "array", tail))
    }
    if (is.array(x)) {
      tail <- if (is.integer(x)) c("integer", "numeric") else c("double", "numeric")
      return(c("array", tail))
    }
    if (isS4(x)) {
      cls <- class(x)
      contains <- names(getClass(cls)@contains)
      return(c(cls, contains))
    }
    if (!is.object(x)) {
      if (is.logical(x)) {
        return("logical")
      }
      if (is.integer(x)) {
        return(c("integer", "numeric"))
      }
      if (is.double(x)) {
        return(c("double", "numeric"))
      }
      if (is.character(x)) {
        return("character")
      }
      if (is.complex(x)) {
        return("complex")
      }
      if (is.list(x)) {
        return("list")
      }
    }
    class(x)
  }
  no_method <- function(x, y, ...) {
    dots <- list(...)
    if (missing(x) && missing(y) && length(dots) == 0) {
      cls <- "NULL"
    } else if (missing(x)) {
      if (length(dots)) {
        cls <- dispatch_class(dots[[1]])
      } else if (!missing(y)) {
        cls <- "name"
      } else {
        cls <- "NULL"
      }
    } else {
      cls <- dispatch_class(x)
    }
    if (length(cls) == 1) {
      msg <- sprintf(
        "no applicable method for 'intersect' applied to an object of class \"%s\"",
        cls
      )
    } else {
      inner <- paste0("'", cls, "'", collapse = ", ")
      msg <- sprintf(
        "no applicable method for 'intersect' applied to an object of class \"c(%s)\"",
        inner
      )
    }
    stop(msg, call. = FALSE)
  }
  registerS3method("intersect", "default", default_neg, envir = ns)

  intersect.mod <- function(x, y, ..., w = 1) {
    mean(abs(as.numeric(unclass(x)))) * w
  }
  intersect.sub <- function(x, y, ...) 100
  intersect.sq <- function(x, y, ...) {
    sqrt(mean(as.numeric(unclass(x))^2))
  }
  intersect.child <- function(x, y, ...) {
    as.numeric(unclass(x))[1] + NextMethod()
  }
  intersect.parent <- function(x, y, ...) sum(as.numeric(unclass(x)))
  intersect.double <- function(x, y, ...) {
    if (missing(x)) -8 else sum(as.numeric(x)) + 1
  }
  intersect.integer <- function(x, y, ...) sum(as.numeric(x)) - 1
  intersect.numeric <- function(x, y, ...) {
    if (missing(x)) -9 else sum(as.numeric(x))
  }
  intersect.array <- function(x, y, ...) sum(as.numeric(x)) + 0.25
  intersect.AccP <- function(x, y, ...) x@x * 2
  intersect.default <- function(x, y, ...) -1
  intersect.NULL <- function(x, y, ...) if (missing(x)) -2 else -3
  intersect.name <- function(x, y, ...) if (missing(x)) -7 else -6
  intersect.strict <- function(x) x
  intersect.only <- function(x, y, ...) NextMethod()

  mod <- structure(c(1, -2, 3.5), class = "mod")
  nums <- c(
    intersect(mod),
    intersect(mod, w = 2),
    intersect(mod, 2),
    intersect(x = mod, w = 4),
    intersect(structure(c(1, -2, 3.5), class = c("sub", "mod"))),
    intersect(structure(c(1, -2, 3.5), class = c("nope", "mod"))),
    intersect(structure(c(3, 4), class = c("nope", "sq"))),
    intersect(structure(c(1.5, 2.5), class = c("child", "parent"))),
    intersect(c(1.5, 2.5)),
    intersect(1:3),
    intersect(matrix(1:4, nrow = 2)),
    intersect(matrix(c(1.5, 2.5), nrow = 1)),
    intersect(array(c(1.5, 2.5), c(1, 1, 2))),
    intersect(new("AccC", x = 1.25)),
    intersect(structure(9, class = "unknown")),
    intersect(NULL),
    intersect(),
    intersect(z = 1.5),
    intersect(1, x = c(1.5, 2.5)),
    intersect(xx = 1),
    intersect(x = c(1.5, 2.5)),
    intersect(as.name("x"))
  )

  rm(intersect.double, intersect.integer, intersect.array)
  nums <- c(
    nums,
    intersect(c(1.5, 2.5)),
    intersect(1:3),
    intersect(matrix(c(1.5, 2.5), nrow = 1)),
    intersect(array(c(1.5, 2.5), c(1, 1, 2))),
    intersect(z = 1.5),
    intersect(x = , z = 1.5)
  )

  rm(intersect.numeric, intersect.default, intersect.NULL, intersect.AccP, intersect.name)
  registerS3method("intersect", "default", no_method, envir = ns)
  errs <- c(
    err(intersect(c(1.5, 2.5), 0)),
    err(intersect(1:3, 0)),
    err(intersect(matrix(1:4, nrow = 2), 0)),
    err(intersect(array(c(1.5, 2.5), c(1, 1, 2)), 0)),
    err(intersect(TRUE, 0)),
    err(intersect("ab", 0)),
    err(intersect(NULL, 0)),
    err(intersect()),
    err(intersect(z = 1.5)),
    err(intersect(z = "ab")),
    err(intersect(structure(1, class = c("aa", "bb")), 0)),
    err(intersect(structure(1, class = ""), 0)),
    err(intersect(structure(1, class = "a'b"), 0)),
    err(intersect(structure(1, class = c("a'b", "c")), 0)),
    err(intersect(new("AccC", x = 1), 0)),
    err(intersect(list(1), 0)),
    err(intersect(1 + 2i, 0)),
    err(intersect(mean, 0)),
    err(intersect(x = , y = 0)),
    err(intersect(x = 1, x = 2, y = 3)),
    err(intersect(y = 1, y = 2, x = 1)),
    err(intersect(structure(1, class = "strict"), 2)),
    err(intersect(structure(1, class = "strict"), 2, z = 3)),
    err(intersect(structure(1, class = "strict"), w = 4)),
    err(intersect(structure(1, class = c("only", "other")), 0))
  )
  registerS3method(
    "intersect",
    "default",
    function(x, y, ...) force(x),
    envir = ns
  )
  errs <- c(errs, err(intersect()))

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
intersect.demo <- function(x, y, ...) {
  c(n = length(x), total = sum(as.numeric(unclass(x))))
}
msg <- tryCatch(intersect(1:3), error = function(e) conditionMessage(e))
hit <- intersect(structure(c(1, 2, 4), class = "demo"))
writeLines(
  c(msg, paste0("n ", hit[["n"]]), paste0("total ", hit[["total"]])),
  file.path(out_dir, "intersect-r.txt")
)
