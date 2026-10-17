.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(openssl))
one <- function() {
  key <- sha256(charToRaw("This is super secret")); iv <- as.raw(1:16); y <- aes_cbc_encrypt(charToRaw("hello curl"), key = key, iv = iv); rawToChar(aes_cbc_decrypt(y, key = key, iv = iv))
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
