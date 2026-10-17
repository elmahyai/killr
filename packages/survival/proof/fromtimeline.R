suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

data1 <- subset(pbcseq,, c(id, day, age, bili, albumin, edema, ast))
data1$bstat <- as.numeric(cut(data1$bili, c(0, 1, 4, 100)))
temp <- subset(pbcseq, !duplicated(id), c(id, futime, status))
names(temp) <- c("id", "day", "bstat")
temp$bstat <- 4*(temp$bstat==2)
pdata <- merge(data1, temp, all=TRUE)
pdata$bstat <- factor(pdata$bstat, 0:4, c("censor", "normal", "1-4", "4+", "death"))
pdata$edema[pdata$id==1] <- NA
indx <- which(pdata$id ==2)
indx <- indx[indx%%2== 1]
pdata$albumin[indx] <- NA
pdata$ast[which(pdata$id==3)[1]] <- NA
pdata$bstat2 <- pdata$bstat
pdata$bstat2[2] <- NA
pdata <- subset(pdata, id < 4)

serialize <- function(cdata) {
  out <- c(paste(names(cdata), collapse="|"))
  for (nm in names(cdata)) {
    col <- cdata[[nm]]
    if (is.factor(col)) col <- as.character(col)
    if (is.numeric(col)) {
      out <- c(out, paste(sprintf("%.17g", col), collapse=","))
    } else {
      out <- c(out, paste(col, collapse=","))
    }
  }
  out
}

one <- function() serialize(fromtimeline(Surv(day, bstat) ~ ., pdata, id=id))

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse="\n"), "\n", sep="")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
