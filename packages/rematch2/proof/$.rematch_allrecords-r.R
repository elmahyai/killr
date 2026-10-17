        suppressPackageStartupMessages(library(rematch2))
pos <- re_exec_all(c("  Ben Franklin and Jefferson Davis", "\tMillard Fillmore"), "(?<first>[[:upper:]][[:lower:]]+) (?<last>[[:upper:]][[:lower:]]+)")
        one <- function() {
          paste(vapply(`$.rematch_allrecords`(pos$first, "match"), paste, "", collapse = "+"), collapse = ",")
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
