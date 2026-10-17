.libPaths(c(path.expand("~/R/library"), .libPaths()))
      suppressPackageStartupMessages(library(modelr))
      if (as.character(packageVersion("modelr")) != "0.1.11") stop("expected modelr 0.1.11")
      options(warn = -1)
      one <- function() {
        g <- data_grid(mtcars, vs, am)
mod <- lm(mpg ~ wt + cyl + vs, data = mtcars)
g2 <- data_grid(mtcars, .model = mod)
c(g$vs, g$am, g2$wt, g2$cyl, g2$vs)
      }
      value <- one()
      elapsed <- numeric(20)
      for (i in seq_len(20)) {
        t0 <- as.numeric(Sys.time())
        one()
        elapsed[[i]] <- as.numeric(Sys.time()) - t0
      }
      cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
