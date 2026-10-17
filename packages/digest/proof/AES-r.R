.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(digest))
stopifnot(as.character(packageVersion("digest")) == "0.6.39")
hextextToRaw <- function(text) {
  vals <- matrix(as.integer(as.hexmode(strsplit(text, "")[[1]])), ncol=2, byrow=TRUE)
  vals <- vals %*% c(16, 1)
  as.raw(vals)
}
plaintext <- hextextToRaw("00112233445566778899aabbccddeeff")
key <- hextextToRaw("000102030405060708090a0b0c0d0e0f")
one <- function() {
  aes <- AES(key)
  aes$encrypt(plaintext)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"hex":"%s","median_ms":%.17g}\n', paste(sprintf("%02x", as.integer(value)), collapse=""), median(elapsed) * 1000))
