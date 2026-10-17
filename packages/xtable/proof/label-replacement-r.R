suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

example <- "/home/ahmed/killr_projects/killr/packages/xtable/docs/output/label-replacement-r.txt"
x <- xtable(data.frame(a = 1:3, b = 4:6))
label(x) <- "tab:example"
sink(example)
print(label(x))
label(x) <- character(0)
print(label(x))
sink()

message_of <- function(expr) {
  tryCatch(expr, error = function(e) conditionMessage(e))
}

make_xt <- function(i) {
  xtable(data.frame(a = seq_len(3 + (i %% 4)), b = seq_len(3 + (i %% 4))))
}

one <- function() {
  out <- list()
  labs <- list(
    "tab:short",
    character(0),
    NA_character_,
    NA,
    "caf\u00e9_label",
    "",
    42L,
    c("tab:vector")
  )
  for (i in seq_along(labs)) {
    x <- make_xt(i)
    x <- `label<-`(x, labs[[i]])
    out[[paste0("lab_", i)]] <- attr(x, "label", exact = TRUE)
  }
  xmat <- structure(
    matrix(seq_len(12), 3, 4),
    class = c("xtable", "matrix"),
    align = c("l", "l", "l", "l", "l"),
    digits = c(0, 0, 0, 0, 0),
    display = c("d", "d", "d", "d", "d")
  )
  xmat <- `label<-`(xmat, "tab:matrix")
  out$matrix_lab <- attr(xmat, "label", exact = TRUE)
  out$err_len <- as.character(message_of(`label<-`(make_xt(99L), 1:2)))
  out$err_class <- as.character(message_of(`label<-`(structure(1, class = "foo"), "x")))
  repeated <- character(0)
  for (j in seq_len(400)) {
    x <- make_xt(j)
    x <- `label<-`(x, paste0("tab-", j))
    val <- attr(x, "label", exact = TRUE)
    if (length(val) == 0) {
      repeated <- repeated
    } else {
      repeated <- c(repeated, val)
    }
  }
  out$repeated <- repeated
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"median_ms":%.17g,"value":', median(elapsed) * 1000))
cat(toJSON(value, auto_unbox = FALSE, na = "null", null = "null"))
cat("}\n")
