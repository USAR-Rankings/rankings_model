#Fwango Results Converter------------
#Takes manually downloaded csvs and converts into standar format
#Reads from Tourney Results/Manual Downloads and writes to Tourney Results as .csv

manual_downloads = data.frame(`Fwango File Title` = gsub(".csv", "", dir('Tourney Results/Manual Downloads')),
                              downloaded = T)

tourney_status =  sheet_scrape2 %>% 
  select(Year, Date, `For Model Use`, `URL identifier`, tourney, `Fwango File Title`) %>% 
  left_join(
    data.frame(URL.identifier = toupper(gsub(".csv", "", dir('Tourney Results'))),
               complete = T) %>% 
      filter(URL.identifier != 'Manual Downloads'),
    by = c('tourney' = 'URL.identifier')
  ) %>% 
  left_join(manual_downloads,
            by = c('Fwango File Title' = 'Fwango.File.Title'))

to_do_list = tourney_status %>% 
  filter(downloaded,
         is.na(complete))


for(td in 1:nrow(to_do_list)){
  file_name = file.path('Tourney Results', 'Manual Downloads', paste0(to_do_list$`Fwango File Title`[td], ".csv"))
  cat('\n', file_name)
  downloaded_dat = read.csv(file_name, as.is = T) %>% 
    mutate(og_order = row_number(),
           tourney = tolower(to_do_list$tourney[td]))
  
  temp = bind_rows(downloaded_dat %>% 
                     transmute(tourney, Division, Round = ifelse(Round %in% 1:50, 'Pool', Round),
                                                                 Team1 = Team.A, Team2 = Team.B, T1P1 = Team.A...Player.1,
                                                                 T1P2 = Team.A...Player.2, T2P1 = Team.B...Player.1, T2P2 = Team.B...Player.2,
                                                                 t1score = Game.1...Score.team.A, t2score = Game.1...Score.team.B, og_order),
                   downloaded_dat %>% 
                     transmute(tourney, Division, Round = ifelse(Round %in% 1:50, 'Pool', Round),
                                                                 Team1 = Team.A, Team2 = Team.B, T1P1 = Team.A...Player.1,
                                                                 T1P2 = Team.A...Player.2, T2P1 = Team.B...Player.1, T2P2 = Team.B...Player.2,
                                                                 t1score = Game.2...Score.team.A, t2score = Game.2...Score.team.B, og_order),
                   downloaded_dat %>% 
                     transmute(tourney, Division, Round = ifelse(Round %in% 1:50, 'Pool', Round),
                                                                 Team1 = Team.A, Team2 = Team.B, T1P1 = Team.A...Player.1,
                                                                 T1P2 = Team.A...Player.2, T2P1 = Team.B...Player.1, T2P2 = Team.B...Player.2,
                                                                 t1score = Game.3...Score.team.A, t2score = Game.3...Score.team.B, og_order)) %>% 
    filter(!is.na(t1score), !is.na(t2score)) %>% 
    arrange(og_order) %>% 
    select(-og_order)
  
  write.csv(temp, file.path('Tourney Results', tolower(paste0(to_do_list$tourney[td], ".csv"))), row.names = F)
}
