        suppressPackageStartupMessages(library(rematch2))
notes <- c("  Ben Franklin and Jefferson Davis", "\tMillard Fillmore")
pattern <- "(?<first>[[:upper:]][[:lower:]]+) (?<last>[[:upper:]][[:lower:]]+)"
        one <- function() {
          pos <- re_exec_all(notes, pattern)
paste(vapply(seq_along(pos$first), function(i) paste(pos$first$match[[i]], pos$first$start[[i]], pos$first$end[[i]], sep = ":", collapse = "+"), ""), collapse = ",")
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
