.libPaths(c(path.expand("~/R/library"), .libPaths()))
      suppressPackageStartupMessages(library(modelr))
      if (as.character(packageVersion("modelr")) != "0.1.11") stop("expected modelr 0.1.11")
      options(warn = -1)
      one <- function() {
        mm <- model.matrix(Sepal.Length ~ Species, data = iris)
mm0 <- model.matrix(Sepal.Length ~ Species - 1, data = iris)
c(mm[1, ], mm[51, ], mm[101, ], utf8ToInt(paste(colnames(mm0), collapse = ",")))
      }
      value <- one()
      elapsed <- numeric(20)
      for (i in seq_len(20)) {
        t0 <- as.numeric(Sys.time())
        one()
        elapsed[[i]] <- as.numeric(Sys.time()) - t0
      }
      cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
