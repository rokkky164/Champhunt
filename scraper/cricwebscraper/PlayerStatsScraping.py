# Web Scraping using BeautifulSoup and Panda

# Use Cricinfo player profile url

# Requests can be install using the following command: C:\Python38\Scripts\easy_install.exe requests

import requests
from bs4 import BeautifulSoup
import pandas as pd
import psycopg2
from collections import OrderedDict

# Extracting Cricinfo squad ids of teams from the IPL tournament page
r = requests.get(
    "https://www.espncricinfo.com/ci/content/squad/index.html?object=1210595"
)

soup = BeautifulSoup(r.text, "html.parser")

parsed_html = soup.find("div", class_="content main-section")

squadlist = parsed_html.find_all("span")

squadids = []
squadnames = []

for i in range(len(squadlist) - 1):
    squadids.append(int(squadlist[i].find("a")["href"][18:-5]))
    squadnames.append(squadlist[i].find("a").contents[0])

Squad = {}
for i in range(len(squadids)):
    Squad[squadids[i]] = squadnames[i][:-6]

# print('Squad ids extracted successfully: ')
# print(squadids)

for squad_id in squadids:
    # Extracting Cricinfo ids of players from the squad page
    url = "https://www.espncricinfo.com/ci/content/squad/"
    url = url + str(squad_id) + ".html"
    print(Squad[squad_id])
    print(url)
    r = requests.get(url)

    soup = BeautifulSoup(r.text, "html.parser")

    parsed_html = soup.find("div", class_="content main-section")

    links = parsed_html.find_all("a")

    links = list(filter(lambda x: x.has_attr("href"), links))

    ids = []

    for link in links:
        # print(link['href'][0:19])
        if link["href"][0:19] == "/ci/content/player/":
            ids.append(int(link["href"][19:-5]))

    # for i in range(len(links)):
    #     if links[i].has_attr('href'):
    #         if links[i]['href'][0:19] == '/ci/content/player':
    #             #print(i)
    #             #print(links[i]['href'][19:-5])
    #             ids.append(int(links[i]['href'][19:-5]))

    # i=0
    # while links[i]['href'][19:-5][0] != '/' and i < len(links):
    #     ids.append(int(links[i]['href'][19:-5]))
    #     i = i + 1

    player_ids = list(OrderedDict.fromkeys(ids))

    # Parsing every individual player's profile page for stats
    for player_id in player_ids:
        url = "https://www.espncricinfo.com/ci/content/player/"
        url = url + str(player_id) + ".html"

        print(" " + url)
        r = requests.get(url)

        soup = BeautifulSoup(r.text, "html.parser")

        parsed_html = soup.find("div", class_="pnl490M")

        name = parsed_html.find("h1").contents[0]

        # Extracting player info
        info = parsed_html.find_all("p", class_="ciPlayerinformationtxt")

        # All fields are not listed for all players.  For e.g. some players don't have playing roles listed
        # while some don't have a bowling style, and some don't have an also known as field
        # To tackle this, we are making a dictionary of all the available fields as keys and assigning them the given values
        # Also note that the Major teams given on Cricinfo also include all the players' past teams as well.  This won't be a good column to filter for current squads.
        # Instead, it would be beneficial to have a separate column for the team that the player plays for every tournament
        # For e.g. Chris Lynn would have IPL_team, CPL_team, BBL_team columns in his Playerstats row
        Dict = {}
        for i in range(len(info)):
            Dict[info[i].find("b").contents[0]] = info[i].find("span").contents[0]

        if "Full name" in Dict.keys():
            full_name = Dict["Full name"]
        else:
            full_name = "NA"

        if "Born" in Dict.keys():
            dobpob = Dict["Born"][1:-1]
        else:
            dobpob = "NA"

        if "Playing role" in Dict.keys():
            playing_role = Dict["Playing role"]
        else:
            playing_role = "NA"

        if "Batting style" in Dict.keys():
            batting_style = Dict["Batting style"]
        else:
            batting_style = "NA"

        if "Bowling style" in Dict.keys():
            bowling_style = Dict["Bowling style"]
        else:
            bowling_style = "NA"

        # Separating date of birth and place of birth
        if dobpob != "NA":
            counter = 0
            dob = ""
            pob = ""
            for i in range(len(dobpob)):
                if counter < 2:
                    if dobpob[i] == ",":
                        counter = counter + 1
                        if counter == 1:
                            dob = dob + dobpob[i]
                    else:
                        dob = dob + dobpob[i]
                elif counter == 2:
                    pob = pob + dobpob[i]

        # This is the code to get all the major teams a player has played for in his career.  There is no way to filter a player's current teams.
        # teamlist = info[3].find_all('span')
        # teams = []
        # for team in teamlist:
        #     teams.append(team.contents[0])

        tablerow = [Squad[squad_id]]
        tablerow.extend(
            [
                player_id,
                name,
                full_name,
                dob,
                pob,
                playing_role,
                batting_style,
                bowling_style,
            ]
        )

        # print(tablerow)

        # Extracting player stats
        if parsed_html.find("table", class_="engineTable"):
            # Batting and fielding data will be in the first engineTable
            bat_field = [
                td.text.strip()
                for td in parsed_html.find("table", class_="engineTable").findAll("td")
            ]
            # Bowling data will be in the 2nd engineTable
            bowling = [
                td.text.strip()
                for td in parsed_html.findAll("table", class_="engineTable")[1].findAll(
                    "td"
                )
            ]

            # There are players who have played 1, 2,...6 formats. One or none of them could be T20s
            # The following code checks how many formats a player has played, and extracts T20 data
            # if available, else fills the tablerow with '0's for all stats

            if len(bat_field) == 15:
                if bat_field[0] == "T20s":
                    tablerow = tablerow + bat_field[1:15]
                    tablerow = tablerow + bowling[2:14]
                else:
                    for i in range(26):
                        tablerow.append("0")
            elif len(bat_field) == 30:
                if bat_field[0] == "T20s":
                    tablerow = tablerow + bat_field[1:15]
                    tablerow = tablerow + bowling[2:14]
                elif bat_field[15] == "T20s":
                    tablerow = tablerow + bat_field[16:30]
                    tablerow = tablerow + bowling[16:28]
                else:
                    for i in range(26):
                        tablerow.append("0")
            elif len(bat_field) == 45:
                if bat_field[0] == "T20s":
                    tablerow = tablerow + bat_field[1:15]
                    tablerow = tablerow + bowling[2:14]
                elif bat_field[15] == "T20s":
                    tablerow = tablerow + bat_field[16:30]
                    tablerow = tablerow + bowling[16:28]
                elif bat_field[30] == "T20s":
                    tablerow = tablerow + bat_field[31:45]
                    tablerow = tablerow + bowling[30:42]
                else:
                    for i in range(26):
                        tablerow.append("0")
            elif len(bat_field) == 60:
                if bat_field[0] == "T20s":
                    tablerow = tablerow + bat_field[1:15]
                    tablerow = tablerow + bowling[2:14]
                elif bat_field[15] == "T20s":
                    tablerow = tablerow + bat_field[16:30]
                    tablerow = tablerow + bowling[16:28]
                elif bat_field[30] == "T20s":
                    tablerow = tablerow + bat_field[31:45]
                    tablerow = tablerow + bowling[30:42]
                elif bat_field[45] == "T20s":
                    tablerow = tablerow + bat_field[46:60]
                    tablerow = tablerow + bowling[44:56]
                else:
                    for i in range(26):
                        tablerow.append("0")
            elif len(bat_field) == 75:
                if bat_field[0] == "T20s":
                    tablerow = tablerow + bat_field[1:15]
                    tablerow = tablerow + bowling[2:14]
                elif bat_field[15] == "T20s":
                    tablerow = tablerow + bat_field[16:30]
                    tablerow = tablerow + bowling[16:28]
                elif bat_field[30] == "T20s":
                    tablerow = tablerow + bat_field[31:45]
                    tablerow = tablerow + bowling[30:42]
                elif bat_field[45] == "T20s":
                    tablerow = tablerow + bat_field[46:60]
                    tablerow = tablerow + bowling[44:56]
                elif bat_field[60] == "T20s":
                    tablerow = tablerow + bat_field[61:75]
                    tablerow = tablerow + bowling[58:70]
                else:
                    for i in range(26):
                        tablerow.append("0")
            elif len(bat_field) == 90:
                if bat_field[0] == "T20s":
                    tablerow = tablerow + bat_field[1:15]
                    tablerow = tablerow + bowling[2:14]
                elif bat_field[15] == "T20s":
                    tablerow = tablerow + bat_field[16:30]
                    tablerow = tablerow + bowling[16:28]
                elif bat_field[30] == "T20s":
                    tablerow = tablerow + bat_field[31:45]
                    tablerow = tablerow + bowling[30:42]
                elif bat_field[45] == "T20s":
                    tablerow = tablerow + bat_field[46:60]
                    tablerow = tablerow + bowling[44:56]
                elif bat_field[60] == "T20s":
                    tablerow = tablerow + bat_field[61:75]
                    tablerow = tablerow + bowling[58:70]
                elif bat_field[75] == "T20s":
                    tablerow = tablerow + bat_field[76:90]
                    tablerow = tablerow + bowling[72:84]
                else:
                    for i in range(26):
                        tablerow.append("0")
        else:
            for i in range(26):
                tablerow.append("0")

        # There might be cases where the scraper picks up '-' for player stats because that is what
        # has been given on Cricinfo.  This code replaces all '-'s with '0's

        tablerow = ["0" if x == "-" else x for x in tablerow]

        """for n, i in enumerate(tablerow):
            if i == '-':
                tablerow[n] = '0"""

        # Default data can be added to tablerow like this too
        # tablerow.extend(0,0,0,0,'0',0.00,0,0.00,0,0,0,0,0,0,0,0,0,0,'0','0',0.00,0.00,0.00,0,0,0)

        # Converting the stat fields to appropriate data types
        # matches
        tablerow[9] = int(tablerow[9])
        # batting_innings
        tablerow[10] = int(tablerow[10])
        # notouts
        tablerow[11] = int(tablerow[11])
        # runs
        tablerow[12] = int(tablerow[12])
        # batting_average
        tablerow[14] = float(tablerow[14])
        # balls_faced
        tablerow[15] = int(tablerow[15])
        # batting_sr
        tablerow[16] = float(tablerow[16])
        # hundreds
        tablerow[17] = int(tablerow[17])
        # fifties
        tablerow[18] = int(tablerow[18])
        # fours
        tablerow[19] = int(tablerow[19])
        # sixes
        tablerow[20] = int(tablerow[20])
        # catches
        tablerow[21] = int(tablerow[21])
        # stumpings
        tablerow[22] = int(tablerow[22])
        # bowling_innings
        tablerow[23] = int(tablerow[23])
        # balls_bowled
        tablerow[24] = int(tablerow[24])
        # runs_conceded
        tablerow[25] = int(tablerow[25])
        # wickets
        tablerow[26] = int(tablerow[26])
        # bowling_average
        tablerow[29] = float(tablerow[29])
        # economy
        tablerow[30] = float(tablerow[30])
        # bowling_sr
        tablerow[31] = float(tablerow[31])
        # fourfers
        tablerow[32] = int(tablerow[32])
        # fifers
        tablerow[33] = int(tablerow[33])
        # tenfers
        tablerow[34] = int(tablerow[34])

        # Inserting row into the playerstats table
        sql = "INSERT INTO market_playerstats (ipl_team, id, name, full_name, dob, pob, playing_role, batting_style, bowling_style, matches, batting_innings, notouts, runs, highest, batting_average, balls_faced, batting_sr, hundreds, fifties, fours, sixes, catches, stumpings, bowling_innings, balls_bowled, runs_conceded, wickets, bbi, bbm, bowling_average, economy, bowling_sr, fourfers, fifers, tenfers) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"

        conn = psycopg2.connect(
            database="wallstreet",
            user="postgres",
            password="admin",
            host="localhost",
            port="5432",
        )
        cursor = conn.cursor()
        cursor.execute(sql, tablerow)
        conn.commit()
        cursor.close()
        conn.close()

### THIS MAY BE USEFUL IN THE FUTURE, NOT NEEDED RIGHT NOW
# headers = ['matches', 'innings', 'not_out', 'runs', 'high_score', 'batting_average', 'balls_faced', 'strike_rate', 'centuries', 'fifties', 'fours', 'sixes', 'catches', 'stumpings']
# bat_field = [td.text.strip() for td in parsed_html.find('table', class_='engineTable').findAll('td')]
# num_formats = int(len(bat_field)/15) #The number of formats for which data is available
# format_positions = [15*x for x in range(num_formats)] #This is to indicate where the data for a particular format starts
# formats = [bat_field[x] for x in format_positions] #This is the list of all formats for which data is available
# avg_starts = [x+1 for x in format_positions[:num_formats]] #Position at which the avg (or data) for a particular format starts
# avg_finish = [x+14 for x in avg_starts] #Position at which the avg (or data) for a particular format finishes
# test_averages = bat_field[1:15]
# format_averages = [bat_field[x:y] for x,y in zip(avg_starts, avg_finish)] #All data separated by formats
# combined = list(zip(formats, format_averages)) #Combining the formats and their data separately
# l = [{x: dict(zip(headers, y))} for x,y in combined]

# headers = ['matches', 'innings', 'balls_delivered', 'runs', 'wickets', 'best_innings', 'best_match', 'bowling_average', 'economy', 'strike_rate', 'four_wickets', 'five_wickets', 'ten_wickets']
# bowling = [td.text.strip() for td in self.parsed_html.findAll('table', class_='engineTable')[1].findAll('td')]
# num_formats = int(len(bowling)/14)
# format_positions = [14*x for x in range(num_formats)]
# formats = [bowling[x] for x in format_positions]
# avg_starts = [x+1 for x in format_positions[:num_formats]]
# avg_finish = [x+13 for x in avg_starts]
# format_averages = [bowling[x:y] for x,y in zip(avg_starts, avg_finish)]
# combined = list(zip(formats, format_averages))
# l = [{x: dict(zip(headers, y))} for x,y in combined]

# If a match's scoreboard is to be scraped:
# https://medium.com/swlh/web-scraping-cricinfo-data-c134fce79a33

# Good source for data, but outdated
# https://www.kaggle.com/cclayford/cricinfo-statsguru-data/?select=Men+T20I+Player+Innings+Stats+-+21st+Century.csv

# One of the most annoying Python errors resolved well:
# https://www.pythoncircle.com/post/424/solving-django-error-noreversematch-at-url-with-arguments-and-keyword-arguments-not-found/

# Implementation of fuzzy search
# https://www.freshconsulting.com/how-to-create-a-fuzzy-search-as-you-type-feature-with-elasticsearch-and-django/
