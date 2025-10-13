library(tidyverse)
write_csvs = T

# Preload----------------------
# A custom preload script is sourced here to load in necessary packages and functions
source('Scripts/Preload.R')

# Read in Tournament list
sheet_scrape2 = read.csv('Tourney List.csv', as.is = T, fileEncoding = "UTF-8")

#Perform Player Corrections
all_cors = read.csv('Players/name_corrections.csv', as.is = T,fileEncoding = "UTF-8") %>%
  select(-Tourney) %>%
  mutate_all(toupper)

library(stringi)
normalize_text <- function(x) {
  x %>%
    iconv(from = "", to = "UTF-8", sub = "") %>%       # Fixes encoding
    stri_trans_general("Latin-ASCII") %>%              # Removes accents: É → E
    toupper()                                          # Standard casing
}
div_cols <- c("Open.Division.1", "Open.Division.2", "Open.Division.3", "Open.Division.4", "Women.Division.1","Women.Division.2")
sheet_scrape2[div_cols] <- lapply(sheet_scrape2[div_cols], normalize_text)

for(d in 1:2){
  gender = c('women', 'open')[d]
# Here we determine which tournaments/divisions should count towards the model.
qual_tourneys = sheet_scrape2 %>%
  filter(`For.Model.Use` == 'X') %>%
  {if(gender == 'open') select(., Date, tourney, `Open.Division.1`:`Open.Division.4`) else .} %>%
  {if(gender == 'women') select(., Date, tourney, `Women.Division.1`,`Women.Division.2`) else .} %>%
  pivot_longer(!c(tourney, Date), names_to = 'd', values_to = 'Division') %>%
  filter(Division != '') %>%
  select(Date, tourney, Division) %>%
  mutate(valid = T) %>%
  mutate_all(toupper) %>%
  mutate(Date = as.Date(Date, format = '%m/%d/%Y')) %>%
  add_row(data.frame(tourney = 'END OF SEASON', Date = as.Date(max(.$Date))+1))
# Here we pull and combine the scraped csvs from those tournaments and divisions


tg = list()

files = dir('Tourney Results') %>%
  data.frame(url = .) %>%
  filter(url != 'Manual Downloads' & url != 'Preprocessed') %>%
  pull(url)

for (i in 1:length(files)) {
  df <- read.csv(paste0('Tourney Results/', files[i]), as.is = TRUE, stringsAsFactors = FALSE, fileEncoding = "UTF-8")
  
  # Clean up encoding and normalize Division column
  if ("Division" %in% names(df)) {
    df$Division <- normalize_text(df$Division)
  }
  
  tg[[i]] <- df
}

forfeit_exceptions = c('USAR2023NATIONALS')

dat = bind_rows(tg) %>%
  mutate_at(vars(tourney:T2P2), toupper) %>%
  filter(tourney %in% forfeit_exceptions | !((t1score == -1 & t2score == 0) | (t2score == -1 & t1score == 0)))

dat <- dat %>%
  mutate(Division = normalize_text(Division),
         tourney = normalize_text(tourney))

qual_tourneys <- qual_tourneys %>%
  mutate(Division = normalize_text(Division),
         tourney = normalize_text(tourney))


# Filtering to valid tourney and division, applying name corrections, and adding a dummy "END OF SEASON" tournament
pp = dat %>%
  left_join(qual_tourneys, by = c('tourney', 'Division')) %>%
  filter(valid == T) %>%
  mutate(T1_result = sign(t1score - t2score)/2 + .5,
         Weight = case_when(Round == 'Pool' ~ 1,
                            TRUE ~ 1)) %>%
  left_join(all_cors, by = c('T1P1' = 'OldName')) %>%
  mutate(T1P1 = case_when(!is.na(NewName) ~ NewName,
                          TRUE ~ T1P1)) %>%
  select(-NewName) %>%
  left_join(all_cors, by = c('T1P2' = 'OldName')) %>%
  mutate(T1P2 = case_when(!is.na(NewName) ~ NewName,
                          TRUE ~ T1P2)) %>%
  select(-NewName) %>%
  left_join(all_cors, by = c('T2P1' = 'OldName')) %>%
  mutate(T2P1 = case_when(!is.na(NewName) ~ NewName,
                          TRUE ~ T2P1)) %>%
  select(-NewName) %>%
  left_join(all_cors, by = c('T2P2' = 'OldName')) %>%
  mutate(T2P2 = case_when(!is.na(NewName) ~ NewName,
                          TRUE ~ T2P2)) %>%
  select(-NewName) %>%
  mutate(Date = as.Date(Date, format = '%m/%d/%Y')) %>%
  add_row(data.frame(tourney = 'END OF SEASON', Date = (as.Date(max(.$Date))+1))) %>%
  arrange(Date) %>%
  mutate(game_id = row_number()) %>%
  filter(!(game_id %in% c(193, 194)))

final<- pp %>% mutate(T1_result = sign(t1score - t2score)/2 + .5,
                        Weight = case_when(Round == 'Pool' ~ 1,
                                           TRUE ~ 1)) %>%
  left_join(all_cors, by = c('T1P1' = 'OldName')) %>%
  mutate(T1P1 = case_when(!is.na(NewName) ~ NewName,
                          TRUE ~ T1P1)) %>%
  select(-NewName) %>%
  left_join(all_cors, by = c('T1P2' = 'OldName')) %>%
  mutate(T1P2 = case_when(!is.na(NewName) ~ NewName,
                          TRUE ~ T1P2)) %>%
  select(-NewName) %>%
  left_join(all_cors, by = c('T2P1' = 'OldName')) %>%
  mutate(T2P1 = case_when(!is.na(NewName) ~ NewName,
                          TRUE ~ T2P1)) %>%
  select(-NewName) %>%
  left_join(all_cors, by = c('T2P2' = 'OldName')) %>%
  mutate(T2P2 = case_when(!is.na(NewName) ~ NewName,
                          TRUE ~ T2P2)) %>%
  select(-NewName) %>%
  add_row(data.frame(tourney = 'END OF SEASON', Date = (as.Date(max(.$Date))+1))) %>%
  arrange(Date) %>%
  mutate(game_id = row_number()) %>%
  filter(!(game_id %in% c(193, 194)))%>% mutate(mT1P1 = T1P1,
                                                mT1P2 = T1P2,
                                                mT2P1 = T2P2,
                                                mT2P2 = T2P1,
                                                mT1_result = T1_result,
                                                mT1_score = t1score,
                                                mT2_score = t2score
                              
  )%>% select(-c(Team1,Team2,valid,Weight,T1P1,T1P2,T2P1,T2P2,T1_result,t1score,t2score))

write.csv(final,paste("data/",gender,"_full_tournaments.csv",sep = ""),row.names=FALSE)
}
