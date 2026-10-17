        suppressPackageStartupMessages(library(rematch2))
cars <- data.frame(rowname = c("Mazda RX4", "Datsun 710"), mpg = c(21, 22.8), stringsAsFactors = FALSE)
        one <- function() {
          paste(bind_re_match_(cars, "rowname", "^(?<make>\\w+) ?(?<model>.+)?$", keep_match = TRUE)$.match, collapse = "|")
        }
        ans <- one()
        elapsed <- numeric(20)
        for (i in seq_len(20)) {
          t0 <- as.numeric(Sys.time())
          one()
          elapsed[[i]] <- as.numeric(Sys.time()) - t0
        }
        cat(ans, "\n", sep = "")
        cat(sprintf("%.17g\n", median(elapsed) * 1000))
