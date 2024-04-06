# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """
# Created on Fri Apr  5 16:08:23 2024

# @author: jacobliljestrand
# """


import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import streamlit as st
from urllib.parse import urljoin
import time
from openpyxl import Workbook
#%%
def scrape(url, key_word, flag):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.content, "html.parser")
    tables = soup.find_all("table")
    dfs = []
    dfs_fix = []
        
    for table in tables:
        rows = table.find_all("tr")
        data = []
        
        for row in rows:
            cols = row.find_all(["th", "td"])  
            cols = [ele.text.strip() for ele in cols]
            links = row.find_all("a", href=True)
            if links:
                match_report_link = urljoin(url, links[-1]['href'])  
                cols.append(match_report_link)
            else:
                cols.append(None) 
            data.append(cols)
        
        df = pd.DataFrame(data)
        dfs.append(df)
    
    if flag == 'fix':
        dfs_fix.append(dfs[1])
        team_link = pd.concat(dfs_fix, ignore_index=True)
    else:
        team_link = pd.concat(dfs, ignore_index=True)
    
    team_link = team_link.rename(columns={team_link.columns[-1]: "Match report link"})
    team_link = pd.DataFrame(team_link).dropna()
    team_link = team_link[team_link['Match report link'].str.endswith(key_word)]
    return team_link

def filter_data(team_data):
    global df_for_shots,link
    all_matches = []
    for link in range(len(team_data)):
        try:           # Introducing a delay to prevent IP-banning
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
    
            url = team_data.iloc[link,-1]
            ref = team_data.iloc[link,11]
            match_date = team_data.iloc[link,2]
                
            page = requests.get(url, headers=headers)
            soup = BeautifulSoup(page.content, "html.parser")
            try:
                team_stats_div = soup.find("div", {"id": "team_stats"}) 
                rows = team_stats_div.find_all("tr") 
            except Exception as e:
                print(f"Error occurred: {e}")
                continue
            data = []
        
            for row in rows:
                cols = row.find_all(["th", "td"])
                match_report = row.find("a", {"class": "tooltip"})  
                match_report_link = match_report.get("href") if match_report else None  
                cols = [ele.text.strip() for ele in cols]
                cols.append(match_report_link)  
                data.append(cols)
            extra_data = pd.DataFrame(data).iloc[:,:-1]
            extra_data.columns = extra_data.iloc[0]
            df = extra_data.drop(0) 
            
            for i in range(1, len(df) - 1, 2):
                index_str = df.iloc[i, 0]
                df.iloc[i + 1, 0] = index_str  
            
            df_for_shots = df.drop(df.index[df.index % 2 == 1])
            try:
                df_for_shots.index = ['Possession', 'Passing Accuracy', 'Shots on Target', 'Saves', 'Cards']
            except:
                print('Error in: ', team_data[link])
                continue
            df = df_for_shots.loc["Shots on Target"]
            
            first_value_sot = df[0].split()[0]
            second_value_sot = df[1].split()[2]
            first_value_sh = df[0].split()[2]
            second_value_sh = df[1].split()[-1]
            
            new_data_sot = [first_value_sot, second_value_sot]
            new_data_sh = [first_value_sh, second_value_sh]
            
            new_df_shots = pd.DataFrame([new_data_sot, new_data_sh],  columns=df.index, index=["Shots on target", "Shots"])
            #new_df_shots.loc['Date'] = match_date
            #new_df_shots.loc['Referee'] = ref
            
            team_stats_extra_div = soup.find("div", {"id": "team_stats_extra"})  
            
            if team_stats_extra_div:
                inner_divs = team_stats_extra_div.find_all("div")  
                indices_to_extract = [1, 17, 33]  
                div_contents = []
                for index, div in enumerate(inner_divs, start=1):
                    if index in indices_to_extract:
                        div_contents.extend(div.text.strip().split('\n'))
                df = pd.DataFrame(div_contents, columns=["Content"])
                df = df.drop([5, 10], axis=0)
                df = df.replace(' ', '',regex=True)
                sequences = []
                first_numbers = []
                second_numbers = []
        
                for index, row in df.iloc[1:].iterrows():
                    content = row["Content"]
                    letter_sequence = ''.join([char for char in content if char.isalpha()])
                    letter_index = content.find(letter_sequence)
                    first_number = ''.join([char for char in content[:letter_index] if char.isdigit()])
                    second_number = ''.join([char for char in content[letter_index + len(letter_sequence):] if char.isdigit()])
        
                    sequences.append(letter_sequence)
                    first_numbers.append(first_number)
                    second_numbers.append(second_number)
                    
                new_df = pd.DataFrame({"First": first_numbers, "Second": second_numbers}, index=sequences)    
                column_names = new_df_shots.columns
                new_df.columns = column_names
                
            else:
                print("No div with ID 'team_stats_extra' found on the page.")
            
            frames = [new_df_shots,new_df]
            team_stats = pd.concat(frames)
            team_stats.index.name = 'Teams'
            all_matches.append(team_stats)
        except:
            continue
    return all_matches

def breakout_data(all_matches):
    transformed_dfs = []
    for df in all_matches:
        home_team, away_team = df.columns.tolist()
        df_transposed = df.transpose()
        data = df_transposed.values.flatten()
        home_columns = [f"Home {col}" for col in df_transposed.columns]
        away_columns = [f"Away {col}" for col in df_transposed.columns]
        columns = home_columns + away_columns
        transformed_df = pd.DataFrame([data], columns=columns)
        transformed_df["Home Team"] = home_team
        transformed_df["Away Team"] = away_team
        transformed_dfs.append(transformed_df)
    
    big_df = pd.concat(transformed_dfs, ignore_index=True)
    return big_df
st.title('LHD scraping app')
date_input_user = st.text_input('Enter the date (YYYY-MM-DD):')

# Convert the user input date to datetime format
date_input_user = pd.to_datetime(date_input_user)

# Convert the Pandas Timestamp to datetime.date object
date_input = date_input_user.date()
key_words = ["League", "Liga", "Serie-A", "Bundesliga", "Ligue-1", "Championship"]
id_key = ['PL 23/24', 'LA 23/24', 'SA 23/24', 'BS 23/24', 'L1 23/24', 'CH 23/24']
leagues = ["https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures", "https://fbref.com/en/comps/12/schedule/La-Liga-Scores-and-Fixtures",
            "https://fbref.com/en/comps/11/schedule/Serie-A-Scores-and-Fixtures","https://fbref.com/en/comps/20/schedule/Bundesliga-Scores-and-Fixtures",
            "https://fbref.com/en/comps/13/schedule/Ligue-1-Scores-and-Fixtures","https://fbref.com/en/comps/10/schedule/Championship-Scores-and-Fixtures"]
match_list = []
butt=st.button('Get recent matches')
if butt:
    for liga in range(len(leagues)):
        st.info(f'Downloading {key_words[liga]} matches')
        time.sleep(30)
        key_word = key_words[liga]
        
        url = leagues[liga]
        team_link = scrape(url, key_word, 'std')
        team_link.iloc[:,2] = pd.to_datetime(team_link.iloc[:,2]).dt.date
        
        
        new_matches_df = team_link[team_link.iloc[:,2] >= date_input]
        
        try:
            big_df = filter_data(new_matches_df)
        
        
        
            big_breakout = breakout_data(big_df)
            
            columns_to_drop = ['Home Touches', 'Away Touches', 'Home Crosses', 'Away Crosses', 'Home Clearances', 'Away Clearances', 
                                'Home Interceptions', 'Away Interceptions', 'Home AerialsWon', 'Away AerialsWon', 'Home LongBalls','Away LongBalls']
            big_breakout.drop(columns=columns_to_drop, inplace=True)
            
            #%%
            new_column_order = ['Home Team','Away Team', 'Home Fouls','Away Fouls','Home Corners','Away Corners','Home Tackles','Away Tackles', 
                                  'Home Offsides', 'Away Offsides', 'Home GoalKicks','Away GoalKicks', 'Home ThrowIns','Away ThrowIns',
                                  'Home Shots on target','Home Shots','Away Shots on target','Away Shots']
                               
            
            big_breakout = big_breakout[new_column_order]   
            
            new_column_names = {'Home Team': 'home', 'Away Team': 'away', 'Home Fouls': 'fouls_home','Away Fouls':'fouls_away','Home Corners': 'corners_home',
                                'Away Corners': 'corners_away','Home Tackles': 'tackles_home', 'Away Tackles': 'tackles_away', 'Home Offsides':'offsides_home',
                                'Away Offsides':'offsides_away','Home GoalKicks':'goal_kicks_home', 'Away GoalKicks':'goal_kicks_away',
                                'Home ThrowIns': 'trow_ins_home', 'Away TrowIns':'trow_ins_away','Home Shots on target': 'sot_home','Home Shots': 'shots_home,',
                                'Away Shots on target':'sot_away', 'Away Shots on target':'sot_away', 'Away Shots':'shots_away'}
            big_breakout.rename(columns=new_column_names, inplace=True)
            big_breakout['Liga'] = id_key[liga]
            match_list.append(big_breakout)
        except:
            continue
    new_matches_to_excel = pd.concat(match_list)
    new_matches_to_excel.iloc[:, 2:18] = new_matches_to_excel.iloc[:, 2:18].apply(pd.to_numeric, errors='coerce')
    #%%
    # Define a function to handle the download action
    def download_excel(df):
        df.to_excel("data.xlsx", index=False)  # Write DataFrame to Excel file without index
        with open("data.xlsx", "rb") as file:
            btn = file.read()
        st.download_button(
            label="Download Excel",
            data=btn,
            file_name="data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Call the function to display the download button
    download_excel(new_matches_to_excel)
            
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# """
# Created on Fri Apr  5 16:08:23 2024

# @author: jacobliljestrand
# """

# #
# import pandas as pd
# import requests
# from bs4 import BeautifulSoup
# import os
# import streamlit as st
# from urllib.parse import urljoin
# import time
# #%%
# def scrape(url, key_word, flag):
#     headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
#     page = requests.get(url, headers=headers)
#     soup = BeautifulSoup(page.content, "html.parser")
#     tables = soup.find_all("table")
#     dfs = []
#     dfs_fix = []
        
#     for table in tables:
#         rows = table.find_all("tr")
#         data = []
        
#         for row in rows:
#             cols = row.find_all(["th", "td"])  
#             cols = [ele.text.strip() for ele in cols]
#             links = row.find_all("a", href=True)
#             if links:
#                 match_report_link = urljoin(url, links[-1]['href'])  
#                 cols.append(match_report_link)
#             else:
#                 cols.append(None) 
#             data.append(cols)
        
#         df = pd.DataFrame(data)
#         dfs.append(df)
    
#     if flag == 'fix':
#         dfs_fix.append(dfs[1])
#         team_link = pd.concat(dfs_fix, ignore_index=True)
#     else:
#         team_link = pd.concat(dfs, ignore_index=True)
    
#     team_link = team_link.rename(columns={team_link.columns[-1]: "Match report link"})
#     team_link = pd.DataFrame(team_link).dropna()
#     team_link = team_link[team_link['Match report link'].str.endswith(key_word)]
#     return team_link

# def filter_data(team_data):
#     #global df_for_shots,link
#     all_matches = []
#     for link in range(len(team_data)):
#         try:
        
#             if link % 15 == 0:
#                 time.sleep(60)
#                 # Introducing a delay to prevent IP-banning
#             headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
    
#             url = team_data.iloc[link,-1]
#             ref = team_data.iloc[link,11]
#             match_date = team_data.iloc[link,2]
                
#             page = requests.get(url, headers=headers)
#             soup = BeautifulSoup(page.content, "html.parser")
#             try:
#                 team_stats_div = soup.find("div", {"id": "team_stats"}) 
#                 rows = team_stats_div.find_all("tr") 
#             except Exception as e:
#                 print(f"Error occurred: {e}")
#                 continue
#             data = []
        
#             for row in rows:
#                 cols = row.find_all(["th", "td"])
#                 match_report = row.find("a", {"class": "tooltip"})  
#                 match_report_link = match_report.get("href") if match_report else None  
#                 cols = [ele.text.strip() for ele in cols]
#                 cols.append(match_report_link)  
#                 data.append(cols)
#             extra_data = pd.DataFrame(data).iloc[:,:-1]
#             extra_data.columns = extra_data.iloc[0]
#             df = extra_data.drop(0) 
            
#             for i in range(1, len(df) - 1, 2):
#                 index_str = df.iloc[i, 0]
#                 df.iloc[i + 1, 0] = index_str  
            
#             df_for_shots = df.drop(df.index[df.index % 2 == 1])
#             try:
#                 df_for_shots.index = ['Possession', 'Passing Accuracy', 'Shots on Target', 'Saves', 'Cards']
#             except:
#                 print('Error in: ', team_data[link])
#                 continue
#             df = df_for_shots.loc["Shots on Target"]
            
#             first_value_sot = df[0].split()[0]
#             second_value_sot = df[1].split()[2]
#             first_value_sh = df[0].split()[2]
#             second_value_sh = df[1].split()[-1]
            
#             new_data_sot = [first_value_sot, second_value_sot]
#             new_data_sh = [first_value_sh, second_value_sh]
            
#             new_df_shots = pd.DataFrame([new_data_sot, new_data_sh],  columns=df.index, index=["Shots on target", "Shots"])
#             #new_df_shots.loc['Date'] = match_date
#             #new_df_shots.loc['Referee'] = ref
            
#             team_stats_extra_div = soup.find("div", {"id": "team_stats_extra"})  
            
#             if team_stats_extra_div:
#                 inner_divs = team_stats_extra_div.find_all("div")  
#                 indices_to_extract = [1, 17, 33]  
#                 div_contents = []
#                 for index, div in enumerate(inner_divs, start=1):
#                     if index in indices_to_extract:
#                         div_contents.extend(div.text.strip().split('\n'))
#                 df = pd.DataFrame(div_contents, columns=["Content"])
#                 df = df.drop([5, 10], axis=0)
#                 df = df.replace(' ', '',regex=True)
#                 sequences = []
#                 first_numbers = []
#                 second_numbers = []
        
#                 for index, row in df.iloc[1:].iterrows():
#                     content = row["Content"]
#                     letter_sequence = ''.join([char for char in content if char.isalpha()])
#                     letter_index = content.find(letter_sequence)
#                     first_number = ''.join([char for char in content[:letter_index] if char.isdigit()])
#                     second_number = ''.join([char for char in content[letter_index + len(letter_sequence):] if char.isdigit()])
        
#                     sequences.append(letter_sequence)
#                     first_numbers.append(first_number)
#                     second_numbers.append(second_number)
                    
#                 new_df = pd.DataFrame({"First": first_numbers, "Second": second_numbers}, index=sequences)    
#                 column_names = new_df_shots.columns
#                 new_df.columns = column_names
                
#             else:
#                 print("No div with ID 'team_stats_extra' found on the page.")
            
#             frames = [new_df_shots,new_df]
#             team_stats = pd.concat(frames)
#             team_stats.index.name = 'Teams'
#             all_matches.append(team_stats)
#         except:
#             continue
#     return all_matches

# def breakout_data(all_matches):
#     transformed_dfs = []
#     for df in all_matches:
#         home_team, away_team = df.columns.tolist()
#         df_transposed = df.transpose()
#         data = df_transposed.values.flatten()
#         home_columns = [f"Home {col}" for col in df_transposed.columns]
#         away_columns = [f"Away {col}" for col in df_transposed.columns]
#         columns = home_columns + away_columns
#         transformed_df = pd.DataFrame([data], columns=columns)
#         transformed_df["Home Team"] = home_team
#         transformed_df["Away Team"] = away_team
#         transformed_dfs.append(transformed_df)
    
#     big_df = pd.concat(transformed_dfs, ignore_index=True)
#     return big_df

# # Assuming your DataFrame is named df
# date_input = st.text_input('Enter the date (YYYY-MM-DD):')

# # Convert the user input date to datetime format
# date_input = pd.to_datetime(date_input)
# key_words = ["League", "Liga", "Serie-A", "Bundesliga", "Ligue-1", "Championship"]
# id_key = ['PL 23/24', 'LA 23/24', 'SA 23/24', 'BS 23/24', 'L1 23/24', 'CH 23/24']
# leagues = ["https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures", "https://fbref.com/en/comps/12/schedule/La-Liga-Scores-and-Fixtures",
#            "https://fbref.com/en/comps/11/schedule/Serie-A-Scores-and-Fixtures","https://fbref.com/en/comps/20/schedule/Bundesliga-Scores-and-Fixtures",
#            "https://fbref.com/en/comps/13/schedule/Ligue-1-Scores-and-Fixtures","https://fbref.com/en/comps/10/schedule/Championship-Scores-and-Fixtures"]
# match_list = []
# butt=st.button('Get recent matches')
# if butt:
#     for liga in range(len(leagues)):
#         time.sleep(30)
#         key_word = key_words[liga]
        
#         url = leagues[liga]
#         team_link = scrape(url, key_word, 'std')
#         team_link.iloc[:,2] = pd.to_datetime(team_link.iloc[:,2]).dt.date
        
        
#         new_matches_df = team_link[team_link.iloc[:,2] >= date_input]
        
#         try:
#             big_df = filter_data(new_matches_df)
        
        
        
#             big_breakout = breakout_data(big_df)
            
#             columns_to_drop = ['Home Touches', 'Away Touches', 'Home Crosses', 'Away Crosses', 'Home Clearances', 'Away Clearances', 
#                                'Home Interceptions', 'Away Interceptions', 'Home AerialsWon', 'Away AerialsWon', 'Home LongBalls','Away LongBalls']
#             big_breakout.drop(columns=columns_to_drop, inplace=True)
            
#             #%%
#             new_column_order = ['Home Team','Away Team', 'Home Fouls','Away Fouls','Home Corners','Away Corners','Home Tackles','Away Tackles', 
#                                  'Home Offsides', 'Away Offsides', 'Home GoalKicks','Away GoalKicks', 'Home ThrowIns','Away ThrowIns',
#                                  'Home Shots on target','Home Shots','Away Shots on target','Away Shots']
                               
            
#             big_breakout = big_breakout[new_column_order]   
            
#             new_column_names = {'Home Team': 'home', 'Away Team': 'away', 'Home Fouls': 'fouls_home','Away Fouls':'fouls_away','Home Corners': 'corners_home',
#                                 'Away Corners': 'corners_away','Home Tackles': 'tackles_home', 'Away Tackles': 'tackles_away', 'Home Offsides':'offsides_home',
#                                 'Away Offsides':'offsides_away','Home GoalKicks':'goal_kicks_home', 'Away GoalKicks':'goal_kicks_away',
#                                 'Home ThrowIns': 'trow_ins_home', 'Away TrowIns':'trow_ins_away','Home Shots on target': 'sot_home','Home Shots': 'shots_home,',
#                                 'Away Shots on target':'sot_away', 'Away Shots on target':'sot_away', 'Away Shots':'shots_away'}
#             big_breakout.rename(columns=new_column_names, inplace=True)
#             big_breakout['Liga'] = id_key[liga]
#             match_list.append(big_breakout)
#         except:
#             continue
#     new_matches_to_excel = pd.concat(match_list)
#     new_matches_to_excel.iloc[:, 2:18] = new_matches_to_excel.iloc[:, 2:18].apply(pd.to_numeric, errors='coerce')
#     #%%
#     # Define a function to handle the download action
#     def download_excel(df):
#         df.to_excel("data.xlsx", index=False)  # Write DataFrame to Excel file without index
#         with open("data.xlsx", "rb") as file:
#             btn = file.read()
#         st.download_button(
#             label="Download Excel",
#             data=btn,
#             file_name="data.xlsx",
#             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         )
    
#     # Call the function to display the download button
#     download_excel(new_matches_to_excel)
            
                         
#%%


 
 
 
 
 
 


