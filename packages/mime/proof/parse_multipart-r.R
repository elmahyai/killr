library(mime)
raw <- charToRaw(paste0('--x\r\nContent-Disposition: form-data; name="a"\r\n\r\none\r\n--x\r\nContent-Disposition: form-data; name="f"; filename="a.txt"\r\nContent-Type: text/plain\r\n\r\nhello\r\n--x--\r\n'))
pos <- 1L
inp <- new.env()
inp$read <- function(n) { z <- raw[pos:min(length(raw),pos+n-1L)]; pos <<- pos+length(z); z }
inp$rewind <- function() pos <<- 1L
env <- list(CONTENT_TYPE='multipart/form-data; boundary=x', CONTENT_LENGTH=length(raw), rook.input=inp)
z <- parse_multipart(env)
z$f$datapath <- 'FILE'
print(z)
