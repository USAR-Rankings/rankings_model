
OPEN_P= {
# Filepath to where the data is
"BASE_PATH": "",
"DATA_PATH": "data/open_full_tournaments.csv",

"NUMB_INITAL" : 25,

# core model
"remove":True,
"remove_time": float(365.0 * 1.5),
"team_method":"inv_var",
"avg_mu":False,

# separation
"SEP":2250,

# RD bounds
"RD_MIN":70,
"RD_MAX":350,
"ENTRY_RD":300,

# team uncertainty
"team_var_alpha":0.7,
"inv_var_gamma":0.60,

# RD shrink cap
"cap_redux":True,
"max_reduction_frac":0.45,

# volatility learning
"tau":0.7,

# inactivity inflation
"rd_inflation_mode":"saturating",
"time_constant":0.90,
"buffer_days":25,
"decay_tau_days":365 * 1.5,
"sat_power":0.95,

# blend entry
"blend_entry":True,
"blend_existing_k":6.0,
"blend_max_weight":0.85,
"blend_exclude_provisional":True,
"blend_min_div_players":1,

# compatibility
"convexity":0.70,

# logistic scale
"DE":350,
"DC":450,

# export
"EXPORT_FILENAME" : "open"
}

WOMENS_P= {
# Filepath to where the data is
"BASE_PATH": "",
"DATA_PATH" : "data/women_full_tournaments.csv",

# Set number of events to use to use intial sperateion for (25 is what was used for final model)
"remove":True,
"remove_time": float(365.0 * 2),
"team_method":"inv_var",
"avg_mu":False,

            # RD bounds
"RD_MIN":60,      # ~80.36


            # team uncertainty (inv-var)
"team_var_alpha":1.32,   # ~1.317
"inv_var_gamma":0.60,

            # RD shrink cap
"cap_redux":True,
"max_reduction_frac":0.67,  # ~0.6699

            # volatility learning
"tau":0.60,  # ~0.491

            # inactivity RD inflation curve (your chosen saturating form)
"rd_inflation_mode":"saturating",
"time_constant":0.90,         # time_constant_phi
"buffer_days":25,
"decay_tau_days":365 * 1.5,   # 547.5
"sat_power":1.7,

 # kept for compatibility (ignored in saturating mode)
"convexity":0.70,
"DE":575,
"DC":625,


# Export results filename
"EXPORT_FILENAME" : "womens"}
