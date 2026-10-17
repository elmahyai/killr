library(snakecase)
x <- c("this Is a Strange_string", "AND THIS ANOTHER_One", "RRRStudio.V11", "species42value 23month 7-8", "", NA_character_)
run <- function() { to_sentence_case(x) }
value <- run()
cat("value\n"); dput(value)
untimed <- run()
t <- numeric(20)
for (i in seq_len(20)) { a <- Sys.time(); run(); t[i] <- as.numeric(difftime(Sys.time(), a, units="secs"))*1000 }
cat("r_ms=", median(t), "\n", sep="")
