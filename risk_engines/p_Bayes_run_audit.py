import pandas as pd
import numpy as np
import io
from google.colab import files

print("Please upload the following 4 files:")
print("1. Your Project Input File (.csv or .xlsx)")
print("2. bayes_lr_regenerated_coefficients_expanded.csv")
print("3. cox_refit_coefficients_timesplit_expanded.csv")
print("4. breslow_baseline_survival_2018_2020.csv")

# 1. File Upload
uploaded = files.upload()

# 2. Identify and Load Files
df_projects = None
df_bayes = None

for filename in uploaded.keys():
    if "bayes" in filename.lower() and "coef" in filename.lower():
        df_bayes = pd.read_csv(io.BytesIO(uploaded[filename]))
        print(f"Loaded Bayes Coefficients: {filename}")
    elif "cox" in filename.lower() and "coef" in filename.lower():
        # Not strictly needed for the Bayes waterfall, but good to have
        print(f"Loaded Cox Coefficients (Unused for Bayes Waterfall): {filename}")
    elif "breslow" in filename.lower():
        # Not strictly needed for the Bayes waterfall
        print(f"Loaded Breslow Baseline (Unused for Bayes Waterfall): {filename}")
    else:
        try:
            df_projects = pd.read_csv(io.BytesIO(uploaded[filename]))
            print(f"Loaded Project Input (CSV): {filename}")
        except:
            try:
                df_projects = pd.read_excel(io.BytesIO(uploaded[filename]))
                print(f"Loaded Project Input (Excel): {filename}")
            except:
                print(f"Skipping unknown file type: {filename}")

if df_projects is None or df_bayes is None:
    print("\nERROR: Missing Project Input or Bayes Coefficients file.")
else:
    print("\nStarting calculation...")

    # --- SETUP ---
    PROVSEC_ALPHA = 0.6
    
    # Cost Quintile Logic
    df_projects["project_cost_float"] = pd.to_numeric(df_projects["project_cost"], errors='coerce')
    try:
        ranks = df_projects["project_cost_float"].rank(method="first")
        df_projects["_cost_quintile_bayes"] = pd.qcut(ranks, 5, labels=[0, 1, 2, 3, 4])
    except:
        df_projects["_cost_quintile_bayes"] = np.nan

    bayes_lookup = df_bayes.set_index('feature_name')['LR'].to_dict()

    # --- MAIN LOOP ---
    long_rows = []

    for idx, row in df_projects.iterrows():
        uid = row.get('Unique ID', idx)
        proj_name = row.get('project', 'Unknown')
        
        # Gather LRs
        # 1. Prior
        prior_lr = bayes_lookup.get('PRIOR', 1.0)
        
        # 2. Province
        lr_prov = bayes_lookup.get(f"province_{row['province']}", 1.0)
        name_prov = f"Province ({row['province']})"
        
        # 3. Sector
        lr_sec = bayes_lookup.get(f"sector_{row['sector']}", 1.0)
        name_sec = f"Sector ({row['sector']})"
        
        # 4. Group
        lr_grp = bayes_lookup.get(f"group_{row['group']}", 1.0)
        name_grp = f"Group ({row['group']})"
        
        # 5. Cost
        q = row["_cost_quintile_bayes"]
        k_cost = f"cost_quintile_{q}" if not pd.isna(q) else "cost_quintile_Unknown"
        lr_cost = bayes_lookup.get(k_cost, 1.0)
        
        # 6. Start Year
        try: sy = int(row['start_year'])
        except: sy = "Unknown"
        k_start = f"start_bin_{sy}"
        if k_start not in bayes_lookup: k_start = "start_bin_Unknown"
        lr_start = bayes_lookup.get(k_start, 1.0)
        
        # 7. Interaction
        k_int = f"prov_sec_{row['province']}_{row['sector']}"
        raw_int = bayes_lookup.get(k_int, 1.0)
        shrunk_int = raw_int ** PROVSEC_ALPHA
        
        # 8. Cleantech
        k_clean = f"cleantech_{row['cleantech']}"
        lr_clean = bayes_lookup.get(k_clean, 1.0)
        
        # 9. Greenfield
        try: gf = int(row['greenfield_flag'])
        except: gf = 0
        lr_green = bayes_lookup.get(f"greenfield_flag_{gf}", 1.0)
        
        # 10. FOAK
        try: foak = int(row['FOAK_flag'])
        except: foak = 0
        lr_foak = bayes_lookup.get(f"FOAK_flag_{foak}", 1.0)
        
        # Steps Definition
        steps = [
            ("Base Rate", prior_lr),
            (name_prov, lr_prov),
            (name_sec, lr_sec),
            (name_grp, lr_grp),
            ("Cost Quintile", lr_cost),
            ("Start Year", lr_start),
            ("Interaction", shrunk_int),
            ("Cleantech", lr_clean),
            ("Greenfield", lr_green),
            ("FOAK", lr_foak)
        ]
        
        curr_odds = 1.0
        prev_prob = 0.0
        
        for i, (name, lr) in enumerate(steps):
            if i == 0:
                curr_odds = lr
            else:
                curr_odds *= lr
            
            prob = curr_odds / (1 + curr_odds)
            change = prob - prev_prob
            
            # Formatting
            prob_str = f"{prob:.1%}"
            if i == 0:
                 change_str = f"+{prob:.1%}" # First step is absolute gain from 0
            else:
                 change_str = f"{change:+.1%}"
            
            long_rows.append({
                "Unique ID": uid,
                "Project": proj_name,
                "Step_Index": i,
                "Step_Name": name,
                "Step_LR": round(lr, 3),
                "Cumulative_Probability": prob_str,
                "Step_Change": change_str
            })
            
            prev_prob = prob

    # Output
    df_out = pd.DataFrame(long_rows)
    output_filename = 'bayes_waterfall_buildup.csv'
    df_out.to_csv(output_filename, index=False)
    
    print(f"\nSuccess! Generated {len(df_out)} rows.")
    print(df_out.head(10).to_string(index=False))
    files.download(output_filename)