suppressPackageStartupMessages(library(foreach))
suppressPackageStartupMessages(library(iterators))

fmt <- function(x) {
  if (is.null(x)) return("NULL")
  if (inherits(x, "error")) return(paste0("ERR:", conditionMessage(x)))
  if (is.matrix(x)) {
    rn <- rownames(x)
    cn <- colnames(x)
    rn <- if (is.null(rn)) "" else paste(rn, collapse = ",")
    cn <- if (is.null(cn)) "" else paste(cn, collapse = ",")
    vals <- paste(sprintf("%.17g", as.numeric(x)), collapse = ",")
    return(paste0("M(", nrow(x), ",", ncol(x), ",", vals, ";rn=", rn, ";cn=", cn, ")"))
  }
  if (is.list(x)) {
    if (length(x) == 0) return("L()")
    parts <- vapply(x, fmt, character(1))
    return(paste0("L(", paste(parts, collapse = ","), ")"))
  }
  if (is.character(x)) return(paste0("C(", paste(x, collapse = ","), ")"))
  paste0("V(", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), ")")
}

run <- function(expr) {
  r <- tryCatch(expr, error = function(e) e)
  if (inherits(r, "error")) paste0("ERR:", conditionMessage(r)) else fmt(r)
}

one <- function() {
  m <- matrix(1:6, 2)
  k <- 10
  parts <- c(
    run(foreach(i = 1:3) %do% sqrt(i)),
    run(foreach(i = 1:3, .combine = "c") %do% sqrt(i)),
    run(foreach(i = 1:3) %do% if (i == 2) stop("boom") else i),
    run(foreach(i = 1:4, .errorhandling = "remove", .combine = "c") %do% if (i == 2) stop("boom") else i),
    run(foreach(i = 1:3, .errorhandling = "pass") %do% if (i == 2) stop("boom") else i),
    run(1:3 %do% 1),
    run(foreach(col = iter(m, by = "col"), .combine = "cbind") %do% col),
    run(foreach(row = iter(m, by = "row"), .combine = "rbind") %do% row),
    run(foreach(i = 1:3, .combine = "c") %do% (i + k)),
    run(foreach(i = 1:4, .combine = "c") %do% if (i == 3) stop("nope") else i),
    run(foreach(i = 1:2, .errorhandling = "remove", .combine = "c") %do% stop("a")),
    run(foreach(i = 1:2, .errorhandling = "remove") %do% stop("a")),
    run(foreach(i = 1:3, .errorhandling = "remove", .combine = "c") %do% if (i == 1) stop("a") else i),
    run(foreach(i = integer(0), .combine = "c", .final = length) %do% i),
    run(foreach(i = 1:4, .combine = "c", .final = sum) %do% i),
    run(foreach(icount(2), icount(5), .combine = "c") %do% 9),
    run(foreach(icount(2), j = 10:12, .combine = "c") %do% j)
  )
  paste(parts, collapse = "|")
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
