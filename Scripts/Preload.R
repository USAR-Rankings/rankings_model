#Preload

#library(RSelenium)
#library(jsonlite)
# library(splashr)
#library(rvest)
library(stringr)
library(dplyr)
library(tidyr)
library(tidyverse)
#library(RecordLinkage)
#library(DescTools)
#library(plotly)
#library(viridis)
#library(lme4)
#library(googlesheets4)
#library(googledrive)
#library(lubridate)

timeouts <- function (remDr, milliseconds){
  qpath <- sprintf("%s/session/%s/timeouts", remDr$serverURL,
                   remDr$sessionInfo[["id"]])
  remDr$queryRD(qpath, method = "POST", qdata = toJSON(list(type = "implicit", ms = milliseconds), 
                                                       auto_unbox = TRUE))
}