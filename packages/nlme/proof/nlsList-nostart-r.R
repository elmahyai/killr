.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
stopifnot(isTRUE(packageVersion("nlme") == "3.1-171"))

script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", file_arg[[1]])))
}

here <- script_dir()
data_dir <- file.path(here, "data")
dir.create(data_dir, recursive = TRUE, showWarnings = FALSE)
write.csv(
  data.frame(Seed = as.character(Loblolly$Seed), age = Loblolly$age,
             height = Loblolly$height),
  file.path(data_dir, "nlsList-nostart-loblolly.csv"), row.names = FALSE
)
writeLines(levels(Loblolly$Seed), file.path(data_dir, "nlsList-nostart-loblolly-levels.txt"))
write.csv(
  data.frame(Plant = as.character(CO2$Plant), conc = CO2$conc,
             uptake = CO2$uptake),
  file.path(data_dir, "nlsList-nostart-co2.csv"), row.names = FALSE
)
writeLines(levels(CO2$Plant), file.path(data_dir, "nlsList-nostart-co2-levels.txt"))

# Each case: name, formula, data, start (NULL = no start, the SSasympOff initial).
cases <- list(
  list(name = "loblolly-nostart", formula = height ~ SSasympOff(age, Asym, lrc, c0) | Seed,
       data = Loblolly, start = NULL),
  list(name = "loblolly-start", formula = height ~ SSasympOff(age, Asym, lrc, c0) | Seed,
       data = Loblolly, start = c(Asym = 100, lrc = -1.5, c0 = 0)),
  list(name = "co2-nostart", formula = uptake ~ SSasympOff(conc, Asym, lrc, c0) | Plant,
       data = CO2, start = NULL),
  list(name = "co2-start", formula = uptake ~ SSasympOff(conc, Asym, lrc, c0) | Plant,
       data = CO2, start = c(Asym = 30, lrc = -4.5, c0 = 52))
)

# Per group: coefficients (Asym, lrc, c0), residual standard error, convergence flag.
values_of <- function(fit) {
  out <- numeric(0)
  for (g in names(fit)) {
    f <- fit[[g]]
    out <- c(out, as.numeric(coef(f)), summary(f)$sigma, as.numeric(f$convInfo$isConv))
  }
  out
}

fit_case <- function(case) {
  if (is.null(case$start)) {
    nlsList(case$formula, case$data)
  } else {
    nlsList(case$formula, case$data, start = case$start)
  }
}

example_lines <- function(case, fit) {
  lines <- c(sprintf("case: %s", case$name), sprintf("groups: %d", length(names(fit))))
  for (g in names(fit)) {
    f <- fit[[g]]
    lines <- c(lines, sprintf(
      "%s: %s sigma=%.10g conv=%s", g,
      paste(sprintf("%.10g", coef(f)), collapse = " "),
      summary(f)$sigma, as.logical(f$convInfo$isConv)
    ))
  }
  lines
}

out_dir <- file.path(here, "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
all_lines <- character(0)
results <- character(0)
for (case in cases) {
  fit <- fit_case(case)
  all_lines <- c(all_lines, example_lines(case, fit), "")
  value <- values_of(fit)
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    fit_case(case)
    elapsed[[i]] <- as.numeric(Sys.time()) - t0
  }
  results <- c(results, sprintf(
    "{\"name\":\"%s\",\"value\":[%s],\"median_ms\":%.17g}",
    case$name, paste(sprintf("%.17g", value), collapse = ","),
    median(elapsed) * 1000
  ))
}
writeLines(all_lines, file.path(out_dir, "nlsList-nostart-r.txt"))
cat(sprintf("{\"cases\":[%s]}\n", paste(results, collapse = ",")))
