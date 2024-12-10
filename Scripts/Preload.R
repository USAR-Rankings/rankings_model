#Preload


library(stringr)
library(dplyr)
library(tidyr)
library(tidyverse)


timeouts <- function (remDr, milliseconds){
  qpath <- sprintf("%s/session/%s/timeouts", remDr$serverURL,
                   remDr$sessionInfo[["id"]])
  remDr$queryRD(qpath, method = "POST", qdata = toJSON(list(type = "implicit", ms = milliseconds), 
                                                       auto_unbox = TRUE))
}