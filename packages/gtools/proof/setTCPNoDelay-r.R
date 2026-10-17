.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

odir <- tempfile("nodelay")
dir.create(odir)
writeLines(c(
  "#include <R.h>",
  "#include <errno.h>",
  "#include <sys/socket.h>",
  "#include <netinet/in.h>",
  "#include <netinet/tcp.h>",
  "",
  "void zero_errno(void) { errno = 0; }",
  "",
  "void get_nodelay(int *fd, int *out, int *err) {",
  "  int val = 0;",
  "  socklen_t len = sizeof(val);",
  "  int rc = getsockopt(*fd, IPPROTO_TCP, TCP_NODELAY, &val, &len);",
  "  if (rc != 0) {",
  "    *out = -1;",
  "    *err = errno;",
  "  } else {",
  "    *out = val;",
  "    *err = 0;",
  "  }",
  "}"
), file.path(odir, "nodelay.c"))
writeLines(c(
  "import socket, time, sys",
  "s = socket.socket()",
  "s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)",
  "s.bind(('127.0.0.1', 0))",
  "s.listen(1)",
  "s.settimeout(15)",
  "sys.stdout.write(str(s.getsockname()[1]) + '\\n')",
  "sys.stdout.flush()",
  "c, _ = s.accept()",
  "time.sleep(20)",
  "c.close()"
), file.path(odir, "listen.py"))
owd <- getwd()
setwd(odir)
status <- system2(
  file.path(R.home("bin"), "R"),
  c("CMD", "SHLIB", "nodelay.c"),
  stdout = "/dev/null",
  stderr = "/dev/null"
)
setwd(owd)
if (status != 0) stop("helper compile failed")
dyn.load(file.path(odir, "nodelay.so"))

nodelay <- function(fd) {
  .C("get_nodelay", fd = as.integer(fd), out = integer(1), err = integer(1))$out
}

con <- pipe(paste("python3", "-u", shQuote(file.path(odir, "listen.py"))), open = "r")
port <- scan(con, n = 1, quiet = TRUE)
cl <- make.socket("127.0.0.1", port)

invisible(.C("zero_errno"))

one <- function() {
  bits <- c(
    paste0(setTCPNoDelay(cl, TRUE), "|", nodelay(cl$socket)),
    paste0(setTCPNoDelay(cl, FALSE), "|", nodelay(cl$socket)),
    paste0(setTCPNoDelay(cl), "|", nodelay(cl$socket)),
    paste0(setTCPNoDelay(cl, 2), "|", nodelay(cl$socket)),
    paste0(setTCPNoDelay(cl, 0), "|", nodelay(cl$socket)),
    paste0(setTCPNoDelay(cl, -1), "|", nodelay(cl$socket)),
    paste0(setTCPNoDelay(cl, 0.9), "|", nodelay(cl$socket)),
    paste0(setTCPNoDelay(cl, 1.9), "|", nodelay(cl$socket)),
    paste0(setTCPNoDelay(cl, c(FALSE, TRUE)), "|", nodelay(cl$socket))
  )
  paste(bits, collapse = "|")
}

invisible(one())
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

out_dir <- "/home/ahmed/killr_projects/killr/packages/gtools/docs/output"
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
ex <- c(
  capture.output(print(cl)),
  capture.output(print(setTCPNoDelay(cl, TRUE)))
)
writeLines(ex, file.path(out_dir, "setTCPNoDelay-r.txt"))

bad <- list(socket = 99999L, "x", port = 1L)
class(bad) <- "socket"
bad0 <- list(socket = 0L, "x", port = 1L)
class(bad0) <- "socket"

err <- function(expr) {
  tryCatch(
    {
      force(expr)
      stop("expected an error")
    },
    error = function(e) conditionMessage(e)
  )
}

stale_bad <- err(setTCPNoDelay(bad, TRUE))
after_bad <- paste0(setTCPNoDelay(cl, FALSE), "|", nodelay(cl$socket))
stale_fd0 <- err(setTCPNoDelay(bad0, TRUE))
after_fd0 <- paste0(setTCPNoDelay(cl, TRUE), "|", nodelay(cl$socket))
plain <- err(setTCPNoDelay(1L, TRUE))
plain_list <- err(setTCPNoDelay(list(1), TRUE))
na_msg <- err(setTCPNoDelay(cl, NA))

warns <- character()
char_msg <- tryCatch(
  withCallingHandlers(
    setTCPNoDelay(cl, "yes"),
    warning = function(w) {
      warns <<- c(warns, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  ),
  error = function(e) conditionMessage(e)
)
char_out <- paste(c(paste0("WARN:", warns), paste0("ERR:", char_msg)), collapse = "|")

value <- paste(
  c(value, stale_bad, after_bad, stale_fd0, after_fd0, plain, plain_list, na_msg, char_out),
  collapse = "|"
)

esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
invisible(close.socket(cl))
invisible(close(con))
