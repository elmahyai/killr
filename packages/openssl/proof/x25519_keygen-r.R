.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(openssl))
one <- function() {
  a <- x25519_keygen(); b <- x25519_keygen(); sec <- x25519_diffie_hellman(a, b$pubkey); if (identical(sec, x25519_diffie_hellman(b, a$pubkey)) && length(sec) == 32L) "32" else "bad"
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- enc2utf8(paste(as.character(value), collapse = "|"))
shown <- gsub("\n", " / ", shown, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
