.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(zoo))
stopifnot(packageVersion("zoo") == "1.9-1")

fmt_one <- function(z) {
  if (is.null(z)) return("null")
  if (length(z) != 1) return(paste(vapply(seq_along(z), function(i) fmt_one(z[[i]]), ""), collapse = "|"))
  if (is.character(z)) return(ifelse(is.na(z), "NA", z))
  if (is.logical(z)) return(ifelse(is.na(z), "NA", ifelse(z, "TRUE", "FALSE")))
  z <- as.numeric(z)
  if (is.na(z)) "NA" else if (is.infinite(z)) { if (z > 0) "Inf" else "-Inf" } else sprintf("%.16g", z)
}

fmt_vec <- function(v) {
  if (is.null(v)) return("null")
  if (length(v) == 0) return("")
  paste(vapply(seq_along(v), function(i) fmt_one(v[[i]]), ""), collapse = "|")
}

xb_coords <- function(x, y, col = NULL, border = NA, ybottom = 0, ytop = NULL,
                      height = NULL, last.step = NULL, ylog = FALSE) {
  if (is.function(y)) y <- y(x)
  x <- as.numeric(x)
  if (length(x) == 0) return(NULL)
  if (is.unsorted(x, na.rm = TRUE)) stop("'x' should be ordered (increasing)", call. = FALSE)
  if (is.null(last.step)) last.step <- median(diff(utils::tail(x)))
  if (is.na(last.step)) last.step <- 0
  if (is.logical(y)) {
    y <- y
  } else if (is.numeric(y)) {
    y <- !is.na(y)
  } else {
    y <- as.character(y)
  }
  NAval <- if (is.character(y)) "" else FALSE
  y[is.na(y)] <- NAval
  yrle <- rle(y)
  blockCol <- yrle$values
  blockCol[blockCol == NAval] <- NA
  if (is.logical(y) && is.null(col)) col <- palette()[1]
  if (length(col) > 0) {
    if (is.character(col)) col[col == ""] <- NA
    ok <- !is.na(blockCol)
    blockCol[ok] <- rep(col, length.out = sum(ok))
  }
  idxBounds <- cumsum(c(1, yrle$lengths))
  idxStart <- utils::head(idxBounds, -1)
  idxEnd <- utils::tail(idxBounds, -1)
  idxEnd[length(idxEnd)] <- length(y)
  blockStart <- x[idxStart]
  blockEnd <- x[idxEnd]
  blockEnd[length(blockEnd)] <- utils::tail(blockEnd, 1) + last.step
  if (is.null(ytop)) ytop <- ybottom + height
  if (ylog) {
    ybottom <- 10^ybottom
    ytop <- 10^ytop
  }
  list(left = blockStart, right = blockEnd, bottom = ybottom, top = ytop, col = blockCol, border = border)
}

xb_zoo <- function(x, y = NULL, ...) {
  if (is.null(y)) y <- x
  if (!is.function(y)) y <- coredata(y)
  xb_coords(index(x), y, ...)
}

block_text <- function(name, rec) {
  paste(c(
    paste0("CASE ", name),
    paste0("left=", fmt_vec(rec$left)),
    paste0("right=", fmt_vec(rec$right)),
    paste0("bottom=", fmt_one(rec$bottom)),
    paste0("top=", fmt_one(rec$top)),
    paste0("col=", fmt_vec(rec$col)),
    paste0("border=", fmt_one(rec$border))
  ), collapse = "\n")
}

one <- function() {
  flow <- zoo(c(1, NA, 3, 3, NA, 8), 1:6)
  flat <- zoo(rep(10, 6), 1:6)
  flags <- zoo(1:5, 1:5)
  parts <- c(
    block_text("coverage", xb_zoo(flow, col = "darkgray", ybottom = 0, height = 2)),
    block_text("function", xb_zoo(flat, function(t) t > 3, col = "gray", ybottom = 0, ytop = 1,
                                  border = "slategray")),
    block_text("logical-y", xb_zoo(flags, c(TRUE, TRUE, FALSE, FALSE, TRUE),
                                   col = c("red", "blue"), ybottom = 0, ytop = 2))
  )
  paste(parts, collapse = "\n\n")
}

verify <- function() {
  pdf(NULL)
  on.exit(invisible(dev.off()), add = TRUE)
  .GlobalEnv$xb_traced <- NULL
  suppressMessages(invisible(trace(graphics::rect, quote({
    .GlobalEnv$xb_traced <- list(left = as.numeric(xleft), right = as.numeric(xright),
                    bottom = as.numeric(ybottom)[[1]], top = as.numeric(ytop)[[1]],
                    col = as.character(col))
  }), print = FALSE)))
  on.exit(suppressMessages(invisible(untrace(graphics::rect))), add = TRUE)
  plot(1:10, type = "n")
  flow <- zoo(c(1, NA, 3, 3, NA, 8), 1:6)
  .GlobalEnv$xb_traced <- NULL
  xblocks(flow, col = "darkgray", ybottom = 0, height = 2)
  got <- xb_zoo(flow, col = "darkgray", ybottom = 0, height = 2)
  traced <- .GlobalEnv$xb_traced
  stopifnot(isTRUE(all.equal(traced$left, as.numeric(got$left))))
  stopifnot(isTRUE(all.equal(traced$right, as.numeric(got$right))))
  stopifnot(isTRUE(all.equal(traced$bottom, as.numeric(got$bottom)[[1]])))
  stopifnot(isTRUE(all.equal(traced$top, as.numeric(got$top)[[1]])))
  stopifnot(identical(traced$col, as.character(got$col)))
}

verify()
value <- one()
out <- "/home/ahmed/killr_projects/killr/packages/zoo/docs/output/xblocks-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(value, out)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"median_ms\":%.17g}\n", median(elapsed) * 1000))
