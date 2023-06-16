# Title: Mixed Model Model Fit-----------------------------
# Author: Skylar Shibayama

# This script fits the season-long mixed model and writes 5 csvs to the Predictions (plus year and gender) folder:
# 1. Season-to-date game-level predictions (both sequential and holdout) titled pred_1v2_df.csv
# 2. Current filtered player ratings titled player_ratings_1v2_df.csv
# 3. Current youth player ratings titled youth_player_ratings_1v2_df.csv
# 4. A record of unfiltered full season player ratings titled player_ratings_1v2_df_full.csv
# 5. A backup copy of #2 with date included as a record titled player_ratings_1v2_df_[Date].csv

cat("Starting fit_models_1_v2 task")

# USER INPUT: Gender----------------
# User inputs gender here; 'women' or 'open'
gender = 'women'
write_csvs = TRUE

# Preload----------------------
# A custom preload script is sourced here to load in necessary packages and functions
# This file is called from the DAG directory so keep that in mind when creating relative references
# Turning off package warning print statements
defaultW <- getOption("warn")
options(warn = -1)

# Reading in arguments from the python runner
myArgs <- commandArgs(trailingOnly = TRUE)
dag_id = myArgs[1]
run_id = myArgs[2]
project_directory = myArgs[3]

# Updating the working directory to be the top level folder of the repo
# (So you can call this directly when running the python script or indirectly from terminal)
setwd(project_directory)

# Loading the enviroment and turning warnings back on
source('src/utils/Preload.R')
options(warn = defaultW)
cat("\nFinished R env setup\n")

# Seed Set-------------------
# Seed is set to 1 for consistent retroactive comparisons (should have a marginal effect on mixed model fitting)
set.seed(1)

# Google Sheets Load------------------
# Here we load data from two google sheets:
# 1. Fwango URLs that includes tournament titles, URLs, and model use status
# 2. USA Roundnet Membership_Rankings Committee Filtered List, which (is supposed to) show membership and USA status for all players

# sheet_scrape = drive_find(type = "spreadsheet") %>%
#   filter(name == 'Fwango URLs')

sheet_scrape = read_data(c(input_dir), FWANGO_URLS, sheet_name=FWANGO_URLS_SHEET_NAME)

sheet_scrape2 = sheet_scrape %>%
  as.data.frame()%>%
  mutate(tourney = toupper(`URL identifier`),
         Date = as.Date(Date, format = '%m/%d/%Y')) %>%
  add_row(data.frame(tourney = 'END OF SEASON', Date = as.Date(max(.$Date))+7))

eligible_players_sheet = read_data(c(input_dir), USAR_MEMBERSHIP_FILTERED_LIST, sheet_name=USAR_MEMBERSHIP_FILTERED_LIST_SHEET_NAME)
# eligible_players_sheet = drive_find(type = "spreadsheet") %>%
#   filter(name == 'USA Roundnet Membership_Rankings Committee Filtered List')

usar_players = eligible_players_sheet %>%
  as.data.frame()

# Youth Players Load-----------------
# Here we read a local csv with youth/DOB status of players. This is a terrible system and should be moved to google sheets at the very least. 
# Also the data quality has been terrible.
youth_players = read_data(c(input_dir, '/Players/'), USAR_YOUTH_MEMBERSHIP_FILE) %>%
  mutate(Name = toupper(Full.name),
         DOB = as.Date(Date.of.birth, format = "%m/%d/%Y"),
         Age = time_length(difftime(Sys.Date(), DOB), "years")) %>% 
  filter(Age > 5,
         Age < 18)

# Name Corrections Load--------------------
# Here we load in a csv that includes manual name corrections
all_cors = read_data(c(input_dir, '/Players/'), NAME_CORRECTIONS) %>%
  filter(is.na(Tourney)) %>% 
  select(-Tourney) %>% 
  mutate_all(toupper)


# Set model parameters-----------------------
# Here we set two parameters:
# 1. year_decay, which is the annual linear decay rate for data weighting. Value of 1 means there is no time-weighting, value of 0 means that data from 365 days ago is unconsidered.
# 2. pool_weight, which is the weight of a pool play game compared to bracket. Value of 1 means equal weight, value of .5 means pool play games count half as much as bracket.
year_decay = 1
pool_weight = 1

results = list()
counter = 0
#Looper
for(d in 1:2){
  gender = c('women', 'open')[d]
#   for(ty in 1:3){
  for(ty in 1:1){
    target_years = list(2021, 2022,2021:2022)[[ty]]
    # cat(target_years)
    # cat(gender)
#     for(yd in seq(1, 1, by = .25)){
    for(yd in 1:1){
      year_decay = yd
      # cat(year_decay)
#       for(pw in seq(1, 1, by = .25)){
      for(pw in 1:1){
        pool_weight = pw
        # cat(pool_weight)
        
        counter = counter +1
        # browser()
        # Collating Dataset---------------------------
        
        # Here we determine which tournaments/divisions should count towards the model.
        qual_tourneys = sheet_scrape2 %>% 
          filter(`For Model Use` == 'X',
                 Year %in% target_years) %>% 
          {if(gender == 'open') select(., Date, tourney, `Open Division 1`:`Open Division 3`) else .} %>% 
          {if(gender == 'women') select(., Date, tourney, `Women Division 1`) else .} %>% 
          pivot_longer(!c(tourney, Date), names_to = 'd', values_to = 'Division') %>% 
          filter(Division != '') %>% 
          select(Date, tourney, Division) %>% 
          mutate(valid = T) %>% 
          mutate_all(toupper)
        
        
        # Here we pull and combine the scraped csvs from those tournaments and divisions
        tg = list()
        
#         files = dir(tourney_data_dir) %>%
#           data.frame(url = .) %>%
#           pull(url)

#         for (i in 1:length(files)){
#           tg[[i]] = read.csv(paste0('Tourney Results/', files[i]), as.is = T, stringsAsFactors = F, fileEncoding="UTF-8")
#         }
        
#         dat = bind_rows(tg) %>%
#           mutate_at(vars(tourney:T2P2), toupper) %>%
#           filter(!((t1score %in% c(-1, -2) & t2score == 0) | (t2score %in% c(-1, -2) & t1score == 0)))
        dat = read_all_data_in_dir(tourney_data_dir) %>%
            bind_rows(tg) %>%
            mutate_at(vars(tourney:T2P2), toupper) %>%
            filter(!((t1score %in% c(-1, -2) & t2score == 0) | (t2score %in% c(-1, -2) & t1score == 0)))

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
          add_row(data.frame(tourney = 'END OF SEASON', Date = as.character(as.Date(max(.$Date))+7))) %>% 
          arrange(Date) %>% 
          mutate(game_id = row_number()) %>% 
          filter(!(game_id %in% c(193, 194)))
        
        # Here we set the weights as determined by the parameters (and reapply name corrections? that seems redundant but unharmful)
        full_data = pp %>% 
          filter(valid == T) %>% 
          ungroup() %>% 
          mutate(T1_result = sign(t1score - t2score)/2 + .5,
                 Weight = case_when(Round == 'POOL' ~ pool_weight,
                                    TRUE ~ 1),
                 Weight = pmax(0, Weight * year_decay^(as.numeric(difftime(max(Date), Date), units = 'days')/365)),
                 Constant = 1) %>% 
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
          add_row(data.frame(tourney = 'END OF SEASON', Date = as.character(max(as.Date(.$Date)+7))))
        
        # Here we expand the dataset such that each player appears in each of the player slots T1P1, T2P1, T1P2, T2P2 such that ordering effects are minimized
        expanded_fulldata = full_data %>% 
          mutate(mT1P1 = T1P1,
                 mT1P2 = T1P2,
                 mT2P1 = T2P1,
                 mT2P2 = T2P2,
                 mT1_result = T1_result,
                 mT1_score = t1score,
                 mT2_score = t2score,
                 is_flipped = 0)%>% 
          bind_rows(full_data %>% 
                      mutate(mT1P1 = T1P1,
                             mT1P2 = T1P2,
                             mT2P1 = T2P2,
                             mT2P2 = T2P1,
                             mT1_result = T1_result,
                             mT1_score = t1score,
                             mT2_score = t2score,
                             is_flipped = 0))%>% 
          bind_rows(full_data %>% 
                      mutate(mT1P1 = T1P2,
                             mT1P2 = T1P1,
                             mT2P1 = T2P1,
                             mT2P2 = T2P2,
                             mT1_result = T1_result,
                             mT1_score = t1score,
                             mT2_score = t2score,
                             is_flipped = 0))%>% 
          bind_rows(full_data %>% 
                      mutate(mT1P1 = T1P2,
                             mT1P2 = T1P1,
                             mT2P1 = T2P2,
                             mT2P2 = T2P1,
                             mT1_result = T1_result,
                             mT1_score = t1score,
                             mT2_score = t2score,
                             is_flipped = 0))%>%  
          
          bind_rows(full_data %>% 
                      mutate(mT1P1 = T2P1,
                             mT1P2 = T2P2,
                             mT2P1 = T1P1,
                             mT2P2 = T1P2,
                             mT1_result = 1 -T1_result,
                             mT1_score = t2score,
                             mT2_score = t1score,
                             is_flipped = 1))%>%
          bind_rows(full_data %>% 
                      mutate(mT1P1 = T2P1,
                             mT1P2 = T2P2,
                             mT2P1 = T1P2,
                             mT2P2 = T1P1,
                             mT1_result = 1 - T1_result,
                             mT1_score = t2score,
                             mT2_score = t1score,
                             is_flipped = 1))%>%
          bind_rows(full_data %>% 
                      mutate(mT1P1 = T2P2,
                             mT1P2 = T2P1,
                             mT2P1 = T1P1,
                             mT2P2 = T1P2,
                             mT1_result = 1 - T1_result,
                             mT1_score = t2score,
                             mT2_score = t1score,
                             is_flipped = 1))%>%
          bind_rows(full_data %>% 
                      mutate(mT1P1 = T2P2,
                             mT1P2 = T2P1,
                             mT2P1 = T1P2,
                             mT2P2 = T1P1,
                             mT1_result = 1 - T1_result,
                             mT1_score = t2score,
                             mT2_score = t1score,
                             is_flipped = 1))%>%
          select(-c(T1P1:T2P2), -T1_result, -t1score, -t2score)
        
        
        
        # Fit Model-----------------------
        #Here we fit both the sequential and holdout models.
        
        tourney_list = unique(full_data$tourney)
        pred_list = list()
        player_ratings = list()
        player_ratings_split = list()
        
#         for(i in 1:length(tourney_list)){
        for(i in 1:2){
          cat('\n\nTourney: ', tourney_list[i])  # Readout
          
          # This is the holdout training dataset where we include all scores EXCEPT that of the target tourney
          train_dat_holdout = expanded_fulldata %>% 
            mutate(mT1_score = case_when(tourney == tourney_list[i] ~ NA_integer_,
                                         TRUE ~ mT1_score),
                   mT2_score = case_when(tourney == tourney_list[i] ~ NA_integer_,
                                         TRUE ~ mT2_score),
                   mT1_result = case_when(tourney == tourney_list[i] ~ NA_real_,
                                          TRUE ~ mT1_result))
          # This is the sequential training dataset where we include all scores BEFORE that of the target tourney
          train_dat_sequential =  expanded_fulldata %>% 
            filter(tourney %in% c(tourney_list[1:i])) %>% 
            mutate(mT1_score = case_when(tourney == tourney_list[i] ~ NA_integer_,
                                         TRUE ~ mT1_score),
                   mT2_score = case_when(tourney == tourney_list[i] ~ NA_integer_,
                                         TRUE ~ mT2_score),
                   mT1_result = case_when(tourney == tourney_list[i] ~ NA_real_,
                                          TRUE ~ mT1_result))
          
          # This is the test dataset of the scores of the target tourney
          test_dat = expanded_fulldata %>% 
            filter(tourney == tourney_list[i])
          
          if(i > 1){
            cat('\nFitting Sequential...')
            
            # Sequential Model Fit
            sequential_lme = glmer(mT1_result ~ Constant + (1|mT1P1) + (1|mT2P1) + (1|mT2P2)-1, data = train_dat_sequential, family = binomial(link = "logit"), weights = Weight)
            
            # Creating player ranks based on the above model
            sequential_ranks = ranef(sequential_lme) %>% 
              as.data.frame() %>% 
              select(-term, -condsd) %>% 
              pivot_wider(names_from = grpvar, values_from = condval) %>% 
              left_join(ranef(sequential_lme) %>% 
                          as.data.frame() %>% 
                          select(-term, -condval) %>% 
                          pivot_wider(names_from = grpvar, names_prefix = 'sd_', values_from = condsd),
                        by = 'grp') %>% 
              transmute(Name = grp,
                        score = (mT1P1),
                        sd = (sd_mT1P1),
                        ceiling = score + 1*sd,
                        floor = score - 1*sd)
            
            # Creating an avg strength of partner/schedule record
            std_sos = train_dat_sequential %>% 
              left_join(sequential_ranks %>% 
                          select(Name, partnerPAAWA = score),
                        by = c('mT1P2' = 'Name')) %>% 
              left_join(sequential_ranks %>% 
                          select(Name, opp1PAAWA = score),
                        by = c('mT2P1' = 'Name')) %>% 
              left_join(sequential_ranks %>%  
                          select(Name, opp2PAAWA = score),
                        by = c('mT2P2' = 'Name')) %>% 
              group_by(mT1P1) %>% 
              summarize(n = n(),
                        partner_strength = mean(partnerPAAWA, na.rm = T),
                        opp_strength = mean(c(opp1PAAWA, opp2PAAWA), na.rm = T),
              )
            
            # Logging those player ratings into the larger dataframe
            player_ratings[[i]] = expand.grid(Name = unique(expanded_fulldata$mT1P1),
                                              tourney = unique(test_dat$tourney)) %>% 
              left_join(sequential_ranks %>% 
                          mutate(tourney = tourney_list[i]),
                        by = c('Name','tourney')) %>% 
              mutate(PAAWA = round(exp(score)/(1+exp(score)), 6)) %>% 
              arrange(-PAAWA) %>% 
              left_join(train_dat_sequential %>% 
                          pivot_longer(c(mT1P1:mT2P2), values_to = 'player') %>% 
                          group_by(player) %>% 
                          summarize(n = n_distinct(tourney)),
                        by = c('Name' = 'player')) %>% 
              
              left_join(qual_tourneys %>% 
                          select(tourney, Date),
                        by = 'tourney') %>%
              left_join(train_dat_sequential %>% 
                          group_by(mT1P1) %>% 
                          summarize(std_wins = sum(mT1_result == 1, na.rm = T)/2,
                                    std_losses = sum(mT1_result == 0, na.rm = T)/2),
                        by = c('Name' = 'mT1P1')) %>% 
              left_join(test_dat %>% 
                          group_by(mT1P1) %>% 
                          summarize(teammate = first(mT1P2),
                                    tourney_wins = sum(mT1_result == 1, na.rm = T)/2,
                                    tourney_losses = sum(mT1_result == 0, na.rm = T)/2),
                        by = c('Name' = 'mT1P1')) %>% 
              left_join(std_sos,
                        by = c('Name' = 'mT1P1')) %>% 
              mutate(PAAWA = case_when(is.na(PAAWA) ~ .5,
                                       TRUE ~ PAAWA),
                     score = case_when(is.na(score) ~ 0,
                                       TRUE ~ score),
                     sd = case_when(is.na(score) ~ 0,
                                    TRUE ~ score),
                     floor = case_when(is.na(floor) ~ 0,
                                       TRUE ~ floor))
            
            
            if(tourney_list[i] != 'END OF SEASON'){
              
              # Adding a column to the test data that includes the modeled prediction done via predict function
              test_dat$pred_sequential_old[!rowSums(is.na(test_dat[,c('mT1P1', 'mT1P2','mT2P1','mT2P2')]))] = predict(sequential_lme, newdata =
                                                                                                                        test_dat[!rowSums(is.na(test_dat[,c('mT1P1', 'mT1P2','mT2P1','mT2P2')])),], type = 'response', allow.new.levels = T)
              # Adding a column to the test data that includes the modeled prediction done via averaging each of the 4-position individual effects
              # This also includes a "floor" prediction for fun that is a game estimate where each player's rating is their "floor", i.e. best estimate minus 1 SD
              # This should give a very similar estimate to the above "old" prediction.
              logit_averaged_preds_sequential = test_dat %>%
                left_join(sequential_ranks %>% 
                            select(Name, t1p1score = score, t1p1sd = sd),
                          by = c('mT1P1' = 'Name'))%>% 
                left_join(sequential_ranks %>% 
                            select(Name, t1p2score = score, t1p2sd = sd),
                          by = c('mT1P2' = 'Name'))%>% 
                left_join(sequential_ranks %>% 
                            select(Name, t2p1score = score, t2p1sd = sd),
                          by = c('mT2P1' = 'Name'))%>% 
                left_join(sequential_ranks %>% 
                            select(Name, t2p2score = score, t2p2sd = sd),
                          by = c('mT2P2' = 'Name')) %>% 
                rowwise() %>% 
                mutate(sum_logit = sum(t1p1score, t1p2score, -t2p1score, -t2p2score, na.rm = T),
                       sum_logit_floor = sum(t1p1score, -1*t1p1sd, t1p2score, -1*t1p2sd, -t2p1score, 1*t2p1sd, -t2p2score, 1*t2p2sd, na.rm = T),
                       pred_sequential = exp(sum_logit)/(1+exp(sum_logit)),
                       pred_sequential_floor = exp(sum_logit_floor)/(1+exp(sum_logit_floor))) %>% 
                select(game_id, is_flipped, pred_sequential, pred_sequential_floor) %>% 
                group_by(game_id, is_flipped) %>% 
                slice(1)
              
              
              test_dat = test_dat %>% 
                left_join(logit_averaged_preds_sequential,
                          by = c('game_id', 'is_flipped'))
            }
            
            
          } else{
            # No sequential predictions if first tourney of year
            test_dat$pred_sequential = NA
            test_dat$pred_sequential_floor = NA
            test_dat$pred_sequential_old = NA
            
            # Logging those player ratings into the larger dataframe
            player_ratings[[i]] = data.frame(Name = unique(expanded_fulldata$mT1P1),
                                             score = 0,
                                             sd = 0,
                                             ceiling = NA,
                                             floor = 0,
                                             PAAWA = .5) %>% 
              left_join(train_dat_sequential %>% 
                          pivot_longer(c(mT1P1:mT2P2), values_to = 'player') %>% 
                          group_by(player) %>% 
                          summarize(n = n_distinct(tourney)),
                        by = c('Name' = 'player')) %>% 
              mutate(tourney = tourney_list[i]) %>% 
              left_join(qual_tourneys,
                        by = 'tourney') %>% 
              left_join(train_dat_sequential %>% 
                          group_by(mT1P1) %>% 
                          summarize(std_wins = sum(mT1_result == 1, na.rm = T)/2,
                                    std_losses = sum(mT1_result == 0, na.rm = T)/2),
                        by = c('Name' = 'mT1P1')) %>% 
              left_join(test_dat %>% 
                          group_by(mT1P1) %>% 
                          summarize(teammate = first(mT1P2),
                                    tourney_wins = sum(mT1_result == 1, na.rm = T)/2,
                                    tourney_losses = sum(mT1_result == 0, na.rm = T)/2),
                        by = c('Name' = 'mT1P1'))
          }
          
          cat('\nFitting Holdout...')
          
          # Sequential Model Fit
          holdout_lme = glmer(mT1_result ~ Constant + (1|mT1P1) + (1|mT2P1) + (1|mT2P2)-1, data = train_dat_holdout, family = binomial(link = "logit"), weights = Weight)
          
          # Creating player ranks based on the above model
          holdout_ranks = ranef(holdout_lme) %>% 
            as.data.frame() %>% 
            select(-term, -condsd) %>% 
            pivot_wider(names_from = grpvar, values_from = condval) %>% 
            left_join(ranef(holdout_lme) %>% 
                        as.data.frame() %>% 
                        select(-term, -condval) %>% 
                        pivot_wider(names_from = grpvar, names_prefix = 'sd_', values_from = condsd),
                      by = 'grp') %>% 
            transmute(Name = grp,
                      score = (mT1P1),
                      sd = (sd_mT1P1),
                      ceiling = score + 1*sd,
                      floor = score - 1*sd)
          
          
          if(tourney_list[i] != 'END OF SEASON'){
            
            # Adding a column to the test data that includes the modeled prediction done via predict function
            test_dat$pred_holdout_old[!rowSums(is.na(test_dat[,c('mT1P1', 'mT1P2','mT2P1','mT2P2')]))] = predict(holdout_lme, newdata =
                                                                                                                   test_dat[!rowSums(is.na(test_dat[,c('mT1P1', 'mT1P2','mT2P1','mT2P2')])),], type = 'response', allow.new.levels = T)
            
            # Adding a column to the test data that includes the modeled prediction done via averaging each of the 4-position individual effects
            # This also includes a "floor" prediction for fun that is a game estimate where each player's rating is their "floor", i.e. best estimate minus 1 SE
            # This should give a very similar estimate to the above "old" prediction.
            logit_averaged_preds_holdout = test_dat %>% 
              # filter(game_id %in% c(965)) %>%
              left_join(holdout_ranks %>% 
                          select(Name, t1p1score = score, t1p1sd = sd),
                        by = c('mT1P1' = 'Name'))%>% 
              left_join(holdout_ranks %>% 
                          select(Name, t1p2score = score, t1p2sd = sd),
                        by = c('mT1P2' = 'Name'))%>% 
              left_join(holdout_ranks %>% 
                          select(Name, t2p1score = score, t2p1sd = sd),
                        by = c('mT2P1' = 'Name'))%>% 
              left_join(holdout_ranks %>% 
                          select(Name, t2p2score = score, t2p2sd = sd),
                        by = c('mT2P2' = 'Name')) %>% 
              rowwise() %>% 
              mutate(sum_logit = sum(t1p1score, t1p2score, -t2p1score, -t2p2score, na.rm = T),
                     sum_logit_floor = sum(t1p1score, -1*t1p1sd, t1p2score, -1*t1p2sd, -t2p1score, 1*t2p1sd, -t2p2score, 1*t2p2sd, na.rm = T),
                     pred_holdout = exp(sum_logit)/(1+exp(sum_logit)),
                     pred_holdout_floor = exp(sum_logit_floor)/(1+exp(sum_logit_floor))) %>% 
              select(game_id, is_flipped, pred_holdout, pred_holdout_floor) %>% 
              group_by(game_id, is_flipped) %>% 
              slice(1)
            
            
            test_dat = test_dat %>% 
              left_join(logit_averaged_preds_holdout,
                        by = c('game_id', 'is_flipped'))
            
            #Getting the test data back to one row per game
            reduced_test_dat = test_dat %>%
              ungroup() %>% 
              arrange(game_id, is_flipped) %>%
              group_by(game_id) %>%
              mutate(pred_sequential_comb_old = (sum(pred_sequential_old[is_flipped == 0]) + sum(1 -pred_sequential_old[is_flipped == 1]))/8) %>%
              mutate(pred_holdout_comb_old = (sum(pred_holdout_old[is_flipped == 0]) + sum(1 -pred_holdout_old[is_flipped == 1]))/8) %>%
              slice(1) %>%
              select(-is_flipped, -pred_sequential_old, -pred_holdout_old)
            
            pred_list[[i]] = reduced_test_dat
            
            # cat('\n\nSequential Correct Rate: ', mean(ifelse(reduced_test_dat$pred_sequential == .5 & !is.na(reduced_test_dat$mT1_result), .5,
            #                                                  as.numeric(round(reduced_test_dat$pred_sequential)==reduced_test_dat$mT1_result)), na.rm = T)) 
            # 
            # cat('\nFloor Sequential Correct Rate: ', mean(ifelse(reduced_test_dat$pred_sequential_floor == .5 & !is.na(reduced_test_dat$mT1_result), .5,
            #                                                      as.numeric(round(reduced_test_dat$pred_sequential_floor)==reduced_test_dat$mT1_result)), na.rm = T))
            # 
            # cat('\nOLD Sequential Correct Rate: ', mean(ifelse(reduced_test_dat$pred_sequential_comb_old == .5 & !is.na(reduced_test_dat$mT1_result), .5,
            #                                                    as.numeric(round(reduced_test_dat$pred_sequential_comb_old)==reduced_test_dat$mT1_result)), na.rm = T))
            # 
            # cat('\n\nSequential MAE: ', mean(abs(reduced_test_dat$mT1_result - reduced_test_dat$pred_sequential), na.rm= T))
            # cat('\nFloor Sequential MAE: ', mean(abs(reduced_test_dat$mT1_result - reduced_test_dat$pred_sequential_floor), na.rm= T))
            # cat('\nOLD Sequential MAE: ', mean(abs(reduced_test_dat$mT1_result - reduced_test_dat$pred_sequential_comb_old), na.rm= T))
            # 
            # cat('\n\nSequential Brier: ', mean((reduced_test_dat$mT1_result - reduced_test_dat$pred_sequential)^2, na.rm= T))
            # cat('\nFloor Sequential Brier: ', mean((reduced_test_dat$mT1_result - reduced_test_dat$pred_sequential_floor)^2, na.rm= T))
            # cat('\nOLD Sequential Brier: ', mean((reduced_test_dat$mT1_result - reduced_test_dat$pred_sequential_comb_old)^2, na.rm= T))
            # 
            # 
            # 
            # 
            # cat('\n\nHoldout Correct Rate: ', mean(ifelse(reduced_test_dat$pred_holdout == .5 & !is.na(reduced_test_dat$mT1_result), .5,
            #                                               as.numeric(round(reduced_test_dat$pred_holdout)==reduced_test_dat$mT1_result)), na.rm = T))
            # cat('\nFloor Holdout Correct Rate: ', mean(ifelse(reduced_test_dat$pred_holdout_floor == .5 & !is.na(reduced_test_dat$mT1_result), .5,
            #                                                   as.numeric(round(reduced_test_dat$pred_holdout_floor)==reduced_test_dat$mT1_result)), na.rm = T))
            # cat('\nOLD Holdout Correct Rate: ', mean(ifelse(reduced_test_dat$pred_holdout_comb_old == .5 & !is.na(reduced_test_dat$mT1_result), .5,
            #                                                 as.numeric(round(reduced_test_dat$pred_holdout_comb_old)==reduced_test_dat$mT1_result)), na.rm = T))
            # 
            # cat('\n\nHoldout MAE: ', mean(abs(reduced_test_dat$mT1_result - reduced_test_dat$pred_holdout), na.rm= T))
            # cat('\nFloor Holdout MAE: ', mean(abs(reduced_test_dat$mT1_result - reduced_test_dat$pred_holdout_floor), na.rm= T))
            # cat('\nOLD Holdout MAE: ', mean(abs(reduced_test_dat$mT1_result - reduced_test_dat$pred_holdout_comb_old), na.rm= T))
            # 
            # cat('\n\nHoldout RMSE: ', sqrt(mean((reduced_test_dat$mT1_result - reduced_test_dat$pred_holdout)^2, na.rm= T)))
            # cat('\nFloor Holdout RMSE: ', sqrt(mean((reduced_test_dat$mT1_result - reduced_test_dat$pred_holdout_floor)^2, na.rm= T)))
            # cat('\nOLD Holdout RMSE: ', sqrt(mean((reduced_test_dat$mT1_result - reduced_test_dat$pred_holdout_comb_old)^2, na.rm= T)))
          }
        }
        
        
        # Bind final tables with clean columns--------------
        pred_df = bind_rows(pred_list) %>% 
          select(game_id, Date, tourney, Division, Round, mT1P1, mT1P2, mT2P1, mT2P2, mT1_result, mT1_score, mT2_score, pred_sequential, pred_holdout)
        player_ratings_df = bind_rows(player_ratings) %>% 
          arrange(Date, -PAAWA)
        player_ratings_split_df = bind_rows(player_ratings_split)
        
        
        
        # Error Rate Metrics-------------------------
        
        cat('\n\nOVERALL RESULTS')
        cat('\n\nSequential Correct Rate: ', mean(ifelse(pred_df$pred_sequential == .5 & !is.na(pred_df$mT1_result), .5,
                                                         as.numeric(round(pred_df$pred_sequential)==pred_df$mT1_result)), na.rm = T)) 
        
        # cat('\nFloor Sequential Correct Rate: ', mean(ifelse(pred_df$pred_sequential_floor == .5 & !is.na(pred_df$mT1_result), .5,
        #                                                      as.numeric(round(pred_df$pred_sequential_floor)==pred_df$mT1_result)), na.rm = T))
        # 
        # cat('\nOLD Sequential Correct Rate: ', mean(ifelse(pred_df$pred_sequential_comb_old == .5 & !is.na(pred_df$mT1_result), .5,
        #                                                    as.numeric(round(pred_df$pred_sequential_comb_old)==pred_df$mT1_result)), na.rm = T))
        
        cat('\n\nSequential MAE: ', mean(abs(pred_df$mT1_result - pred_df$pred_sequential), na.rm= T))
        # cat('\nFloor Sequential MAE: ', mean(abs(pred_df$mT1_result - pred_df$pred_sequential_floor), na.rm= T))
        # cat('\nOLD Sequential MAE: ', mean(abs(pred_df$mT1_result - pred_df$pred_sequential_comb_old), na.rm= T))
        
        cat('\n\nSequential RMSE: ', sqrt(mean((pred_df$mT1_result - pred_df$pred_sequential)^2, na.rm= T)))
        # cat('\nFloor Sequential RMSE: ', sqrt(mean((pred_df$mT1_result - pred_df$pred_sequential_floor)^2, na.rm= T)))
        # cat('\nOLD Sequential RMSE: ', sqrt(mean((pred_df$mT1_result - pred_df$pred_sequential_comb_old)^2, na.rm= T)))
        
        
        
        
        cat('\n\nHoldout Correct Rate: ', mean(ifelse(pred_df$pred_holdout == .5 & !is.na(pred_df$mT1_result), .5,
                                                      as.numeric(round(pred_df$pred_holdout)==pred_df$mT1_result)), na.rm = T))
        # cat('\nFloor Holdout Correct Rate: ', mean(ifelse(pred_df$pred_holdout_floor == .5 & !is.na(pred_df$mT1_result), .5,
        #                                                   as.numeric(round(pred_df$pred_holdout_floor)==pred_df$mT1_result)), na.rm = T))
        # cat('\nOLD Holdout Correct Rate: ', mean(ifelse(pred_df$pred_holdout_comb_old == .5 & !is.na(pred_df$mT1_result), .5,
        #                                                 as.numeric(round(pred_df$pred_holdout_comb_old)==pred_df$mT1_result)), na.rm = T))
        
        cat('\n\nHoldout MAE: ', mean(abs(pred_df$mT1_result - pred_df$pred_holdout), na.rm= T))
        # cat('\nFloor Holdout MAE: ', mean(abs(pred_df$mT1_result - pred_df$pred_holdout_floor), na.rm= T))
        # cat('\nOLD Holdout MAE: ', mean(abs(pred_df$mT1_result - pred_df$pred_holdout_comb_old), na.rm= T))
        
        cat('\n\nHoldout RMSE: ', sqrt(mean((pred_df$mT1_result - pred_df$pred_holdout)^2, na.rm= T)))
        # cat('\nFloor Holdout RMSE: ', sqrt(mean((pred_df$mT1_result - pred_df$pred_holdout_floor)^2, na.rm= T)))
        # cat('\nOLD Holdout RMSE: ', sqrt(mean((pred_df$mT1_result - pred_df$pred_holdout_comb_old)^2, na.rm= T)))
        
        
        results[[counter]] = data.frame(year = paste0(target_years, collapse = '_'),
                                        division = gender,
                                        year_decay = year_decay,
                                        pool_weight = pool_weight,
                                        seq_cor = mean(ifelse(pred_df$pred_sequential == .5 & !is.na(pred_df$mT1_result), .5,
                                                              as.numeric(round(pred_df$pred_sequential)==pred_df$mT1_result)), na.rm = T),
                                        seq_mae = mean(abs(pred_df$mT1_result - pred_df$pred_sequential), na.rm= T),
                                        seq_rmse = sqrt(mean((pred_df$mT1_result - pred_df$pred_sequential)^2, na.rm= T)),
                                        holdout_cor = mean(ifelse(pred_df$pred_holdout == .5 & !is.na(pred_df$mT1_result), .5,
                                                                  as.numeric(round(pred_df$pred_holdout)==pred_df$mT1_result)), na.rm = T),
                                        holdout_mae = mean(abs(pred_df$mT1_result - pred_df$pred_holdout), na.rm= T),
                                        holdout_rmse = sqrt(mean((pred_df$mT1_result - pred_df$pred_holdout)^2, na.rm= T)))
        
        print(results[[counter]])
      }
    }
  }
}

# Create Previous Week rankings for trend tracking purposes ---------------------
prev_ranks = player_ratings_df %>%
  filter(tourney == tourney_list[length(tourney_list) - 1]) %>% 
  select(Name:PAAWA, std_wins:std_losses, n_tourneys = n.x, partner_strength:opp_strength) %>%
  left_join(usar_players %>% 
              {if(gender == 'women') filter(., Gender == 'Female') else .} %>% 
              transmute(Name = toupper(`Full name`),
                        `USA Player?`),
            by = 'Name') %>% 
  filter(`USA Player?` == 'Y',
         n_tourneys > 1) %>%
  distinct() %>% 
  mutate(player_rank_t = rank(-PAAWA),
         player_rank = case_when(player_rank_t %% 1 == .5 ~ paste0('T', floor(player_rank_t)),
                                 TRUE ~ as.character(player_rank_t))) %>% 
  select(Name, prev_rank = player_rank)

# Bind previous week and convert to 100-scaled score rankings table ------------------
ranks = player_ratings_df %>%
  filter(tourney == 'END OF SEASON') %>% 
  select(Name:PAAWA, std_wins:std_losses, n_tourneys = n.x, partner_strength:opp_strength) %>%
  left_join(usar_players %>% 
              {if(gender == 'women') filter(., Gender == 'Female') else .} %>% 
              transmute(Name = toupper(`Full name`),
                        `USA Player?`),
            by = 'Name') %>% 
  filter(`USA Player?` == 'Y',
         n_tourneys > 1) %>%
  mutate(player_rank_t = rank(-PAAWA),
         player_rank = case_when(player_rank_t %% 1 == .5 ~ paste0('T', floor(player_rank_t)),
                                 TRUE ~ as.character(player_rank_t)),
         adj_score = round(100 + 10*score, 2),
         adj_partner = round(100 + 10*partner_strength, 2),
         adj_opp = round(100 + 10*opp_strength, 2)
         
  ) %>% 
  left_join(prev_ranks, by = 'Name') %>% 
  select(Name, Score = adj_score, std_wins:n_tourneys, Avg_Partner_Score = adj_partner, Avg_Opponent_Score = adj_opp, player_rank, prev_rank) %>% 
  distinct()


# Filter to youth and gender for youth rankings----------------------
youth_ranks = player_ratings_df %>%
  filter(Name %in% youth_players$Name) %>% 
  filter(tourney == 'END OF SEASON') %>% 
  select(Name:PAAWA, std_wins:std_losses, n_tourneys = n.x, partner_strength:opp_strength) %>%
  left_join(usar_players %>% 
              {if(gender == 'women') filter(., Gender == 'Female') else .} %>% 
              transmute(Name = toupper(`Full name`),
                        `USA Player?`),
            by = 'Name') %>% 
  filter(`USA Player?` == 'Y',
         n_tourneys > 1) %>%
  mutate(player_rank_t = rank(-PAAWA),
         player_rank = case_when(player_rank_t %% 1 == .5 ~ paste0('T', floor(player_rank_t)),
                                 TRUE ~ as.character(player_rank_t)),
         adj_score = round(100 + 10*score, 2),
         adj_partner = round(100 + 10*partner_strength, 2),
         adj_opp = round(100 + 10*opp_strength, 2)
         
  ) %>% 
  left_join(prev_ranks, by = 'Name') %>% 
  select(Name, Score = adj_score, std_wins:n_tourneys, Avg_Partner_Score = adj_partner, Avg_Opponent_Score = adj_opp, player_rank, prev_rank) %>% 
  distinct()



#Write CSVs-----------------------

if(write_csvs){
  #if(gender == 'women'){
    write_data(c(output_dir, paste0(dag_id, '_', run_id), 'fit_models_1_v2/Predictions/2022/Women/'), 'pred_1v2_df.csv', pred_df)
    write_data(c(output_dir, paste0(dag_id, '_', run_id), 'fit_models_1_v2/Predictions/2022/Women/'), 'player_ratings_1v2_df.csv', ranks)
    write_data(c(output_dir, paste0(dag_id, '_', run_id), 'fit_models_1_v2/Predictions/2022/Women/'), 'youth_player_ratings_1v2_df.csv', youth_ranks)
    write_data(c(output_dir, paste0(dag_id, '_', run_id), 'fit_models_1_v2/Predictions/2022/Women/'), 'player_ratings_1v2_df_full.csv', player_ratings_df)
    write_data(c(output_dir, paste0(dag_id, '_', run_id), 'fit_models_1_v2/Predictions/2022/Women/'), paste0('player_ratings_1v2_df_', Sys.Date(), '.csv'), ranks)
  #}
  #if(gender == 'open'){
    write_data(c(output_dir, paste0(dag_id, '_', run_id), 'fit_models_1_v2/Predictions/2022/Open/'), 'pred_1v2_df.csv', pred_df)
    write_data(c(output_dir, paste0(dag_id, '_', run_id), 'fit_models_1_v2/Predictions/2022/Open/'), 'player_ratings_1v2_df.csv', ranks)
    write_data(c(output_dir, paste0(dag_id, '_', run_id), 'fit_models_1_v2/Predictions/2022/Open/'), 'youth_player_ratings_1v2_df.csv', youth_ranks)
    write_data(c(output_dir, paste0(dag_id, '_', run_id), 'fit_models_1_v2/Predictions/2022/Open/'), 'player_ratings_1v2_df_full.csv', player_ratings_df)
    write_data(c(output_dir, paste0(dag_id, '_', run_id), 'fit_models_1_v2/Predictions/2022/Open/'), paste0('player_ratings_1v2_df_', Sys.Date(), '.csv'), ranks)
  #}
}

cat("\nfit_models_1_v2 task completed\n")
