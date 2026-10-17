.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

fmt_one <- function(z) {
  if (length(z) != 1) stop("expected length-1")
  if (is.character(z)) return(ifelse(is.na(z), "NA", z))
  if (is.logical(z)) return(ifelse(is.na(z), "NA", ifelse(z, "TRUE", "FALSE")))
  z <- as.numeric(z)
  if (is.na(z)) "NA" else if (is.infinite(z)) {
    if (z > 0) "Inf" else "-Inf"
  } else {
    sprintf("%.16g", z)
  }
}

flat <- function(x) {
  if (is.null(x)) return("")
  paste(vapply(seq_along(x), function(i) fmt_one(x[[i]]), ""), collapse = "|")
}

one <- function() {
  treatment <- c(
    "Control", "Aspirin 10mg/day", "Aspirin 50mg/day",
    "Aspirin 100mg/day", "Acetomycin 100mg/day",
    "Acetomycin 1000mg/day"
  )
  x <- rev(c(
    "AA 0.50 ml", "AA 1.5 ml", "AA 500 ml", "AA 1500 ml",
    "EXP 1", "AA 1e3 ml", "A A A", "1 2 3 A", "NA", NA, "1e2",
    "", "-", "1A", "1 A", "100", "100A", "Inf"
  ))
  chapters <- c(
    "V. Non Sequiturs", "II. More Nonsense", "I. Nonsense",
    "IV. Nonesensical Citations", "III. Utter Nonsense"
  )
  vals <- c("3E1", "2E3", "4e0")
  roman_lower <- c(
    "xix", "xii", "mcv", "iii", "iv", "dcclxxii", "cdxcii",
    "dcxcviii", "dcvi", "cci"
  )
  paste(
    flat(mixedsort(treatment)),
    flat(mixedsort(x)),
    flat(mixedsort(x, decreasing = TRUE)),
    flat(mixedsort(x, na.last = FALSE)),
    flat(mixedsort(x, blank.last = TRUE)),
    flat(mixedsort(c(3, 1, 2))),
    flat(mixedsort(chapters, numeric.type = "roman")),
    flat(mixedsort(roman_lower, numeric.type = "roman", roman.case = "lower")),
    flat(mixedsort(vals)),
    flat(mixedsort(vals, scientific = FALSE)),
    sep = "|"
  )
}

mixedsort(c("A", "B"))
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', value, median(elapsed) * 1000))
