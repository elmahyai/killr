.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

pack <- function(sym) {
  vals <- numeric(0)
  nglobal <- sym$Nglobal
  vals <- c(vals, if (is.null(nglobal)) -999 else as.numeric(nglobal))
  vals <- c(vals, if (inherits(sym$ModelInit, "NativeSymbol")) 1 else 0)
  vals <- c(vals, if (inherits(sym$Func, "NativeSymbol")) 1 else 0)
  vals <- c(vals, if (is.null(sym$JacFunc)) 0 else 1)
  cols <- sym$Nmtot$colnames
  if (is.null(cols)) {
    vals <- c(vals, -1)
  } else {
    vals <- c(vals, if (is.character(cols)) 0 else 1)
    vals <- c(vals, length(cols))
    nm <- names(cols)
    if (is.null(nm)) nm <- rep("", length(cols))
    for (i in seq_along(cols)) {
      chars <- utf8ToInt(nm[[i]])
      vals <- c(vals, length(chars), chars)
      if (is.character(cols)) {
        piece <- utf8ToInt(cols[[i]])
        vals <- c(vals, length(piece), piece)
      } else {
        vals <- c(vals, as.numeric(cols[[i]]))
      }
    }
  }
  lv <- sym$Nmtot$lengthvar
  if (is.null(lv)) {
    vals <- c(vals, 0)
  } else {
    vals <- c(vals, 1, length(lv))
    lnm <- names(lv)
    if (is.null(lnm)) lnm <- rep("", length(lv))
    for (i in seq_along(lv)) {
      vals <- c(vals, if (is.na(lv[[i]])) -1 else as.numeric(lv[[i]]))
      chars <- utf8ToInt(lnm[[i]])
      vals <- c(vals, length(chars), chars)
    }
  }
  vals
}

one <- function() {
  out6 <- c(
    "PAR", "TotalN", "PhotoSynthesis",
    "NCratio", "ChlCratio", "Chlorophyll"
  )
  parts <- list(
    checkDLL("aquaphy", NULL, "deSolve", "iniaqua", TRUE, 6, out6, 1),
    checkDLL(
      "aquaphy", "iniaqua", "deSolve", NULL, TRUE, 4,
      c("PAR", "PAR", "TotalN", "PhotoSynthesis", "Extra"), 1
    ),
    checkDLL("aquaphy", NULL, "deSolve", "deSolve", FALSE, 4, c("A", "B"), 1),
    checkDLL("aquaphy", NULL, "deSolve", NULL, FALSE, 3, 1:2, 1),
    checkDLL("aquaphy", NULL, "deSolve", NULL, FALSE, 0, "A", 1),
    checkDLL(
      "aquaphy", NULL, "deSolve", "iniaqua", FALSE, 2,
      c(A = "x", B = "x", C = "y"), 1
    ),
    checkDLL("aquaphy", NULL, "deSolve", NULL, FALSE, 0, character(0), 1)
  )
  fa <- checkDLL("aquaphy", NULL, "deSolve", NULL, FALSE, 0, NULL, 1)
  fb <- checkDLL("aquaphyforc", NULL, "deSolve", NULL, FALSE, 0, NULL, 1)
  fc <- checkDLL("iniaqua", NULL, "deSolve", NULL, FALSE, 0, NULL, 1)
  value <- unlist(lapply(parts, pack), use.names = FALSE)
  value <- c(
    value, pack(fa), pack(fb), pack(fc),
    as.numeric(identical(fa$Func, fb$Func)),
    as.numeric(identical(fa$Func, fc$Func))
  )
  as.numeric(value)
}

json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":%s,"median_ms":%.17g}\n',
  json_num(value), median(elapsed) * 1000
))
