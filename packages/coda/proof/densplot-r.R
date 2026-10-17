.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

n <- 400L
i <- seq_len(n)
x <- cbind(
  sin(i / 3) + 0.2 * cos(i),
  (sin(i / 5) + 1) / 2,
  (i - 1L) %% 6
)
colnames(x) <- c("alpha", "beta", "gamma")
m <- as.mcmc(x)

pretty.discrete <- function(y, right) {
  ybreaks <- pretty(y, nclass.Sturges(y))
  yunique <- unique(y)
  if (length(yunique) == 1) {
    return(ybreaks)
  }
  if (length(ybreaks) > length(yunique)) {
    ybreaks <- sort(yunique)
  }
  nb <- length(ybreaks)
  if (right) {
    if (max(y) < ybreaks[nb]) {
      ybreaks[nb] <- max(y)
    }
    if (min(y) > ybreaks[1]) {
      ybreaks[1] <- min(y) - 1
    } else if (min(y) == ybreaks[1]) {
      ybreaks <- c(ybreaks[1] - 1, ybreaks)
    }
  } else {
    if (min(y) > ybreaks[1]) {
      ybreaks[1] <- min(y)
    }
    if (max(y) < ybreaks[nb]) {
      ybreaks[nb] <- max(y) + 1
    } else if (max(y) == ybreaks[nb]) {
      ybreaks <- c(ybreaks[nb] + 1, ybreaks)
    }
  }
  ybreaks
}

extract <- function(obj) {
  xx <- as.matrix(obj)
  out <- numeric(0)
  bwf <- function(sample) {
    sample <- sample[!is.na(as.vector(sample))]
    1.06 * min(sd(sample), IQR(sample) / 1.34) * length(sample)^-0.2
  }
  for (col in seq_len(nvar(obj))) {
    y0 <- xx[, col]
    bw <- bwf(y0)
    discrete <- max(abs(y0 - floor(y0))) == 0 || bw == 0 || length(unique(y0)) == 1
    if (discrete) {
      ybreaks <- pretty.discrete(y0, TRUE)
      yhist <- hist(y0, breaks = ybreaks, right = TRUE, plot = FALSE)
      out <- c(
        out,
        1,
        bw,
        length(yhist$breaks),
        yhist$breaks,
        length(yhist$density),
        yhist$density
      )
    } else {
      y <- y0
      scale <- "open"
      if (max(y) <= 1 && 1 - max(y) < 2 * bw) {
        if (min(y) >= 0 && min(y) < 2 * bw) {
          scale <- "proportion"
          y <- c(y, -y, 2 - y)
        }
      } else if (min(y) >= 0 && min(y) < 2 * bw) {
        scale <- "positive"
        y <- c(y, -y)
      }
      dens <- density(y, width = 4 * bw)
      if (scale == "proportion") {
        dens$y <- 3 * dens$y[dens$x >= 0 & dens$x <= 1]
        dens$x <- dens$x[dens$x >= 0 & dens$x <= 1]
      } else if (scale == "positive") {
        dens$y <- 2 * dens$y[dens$x >= 0]
        dens$x <- dens$x[dens$x >= 0]
      }
      rug <- y[seq_len(niter(obj))]
      out <- c(
        out,
        0,
        bw,
        dens$bw,
        max(dens$y) / 100,
        length(rug),
        rug,
        length(dens$x),
        dens$x,
        length(dens$y),
        dens$y
      )
    }
  }
  out
}

one <- function(svg_path = NULL) {
  if (is.null(svg_path)) {
    pdf(nullfile())
  } else {
    svg(svg_path, width = 7, height = 8)
  }
  on.exit(dev.off(), add = TRUE)
  par(mfrow = c(3, 1))
  densplot(m)
  extract(m)
}

value <- one(file.path(out_dir, "densplot-r.svg"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = file.path(root, "proof", "densplot-r.txt"))
