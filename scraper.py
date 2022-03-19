import pandas as pd
import numpy as np
import requests
import re
from bs4 import BeautifulSoup

SITE_URL = 'https://www.fantasypros.com'
HITTER_URL = 'https://www.fantasypros.com/mlb/projections/hitters.php?points=E'
PITCHER_URL = 'https://www.fantasypros.com/mlb/projections/pitchers.php?points=E'
ADP_URL = 'https://www.fantasypros.com/mlb/rankings/overall.php?eligibility=E'
STAT_DELIM = '|'


def get_links(url, site=''):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    links = []
    errors = []
    for tr in table.findAll("tr"):
        trs = tr.findAll("td")
        for each in trs:
            try:
                link = each.find('a')['href']
                links.append(site + link)
            except Exception as ex:
                errors.append((link, ex))

    return pd.Series(links, name='Link')


def get_player_info(player):
    index = re.search('(.*)\)', player).group(1)+')'
    name = re.search('(.*)\s\(', player).group(1)
    paren = re.search('\((.*)\)', player).group(1)

    status = re.search('\)\s(.*)', player)
    status = status.group(1) if status else None

    # get team and position (logic for free agents)
    team = ''
    pos = ''
    if ' - ' in paren:
        team = paren.split(' - ')[0]
        pos = paren.split(' - ')[1]
    else:
        team = 'FA'
        pos = paren

    # substitute OF pos names
    pos = re.sub('LF|CF|RF', 'OF', pos)
    pos = np.unique(np.array(pos.split(',')).tolist())
    pos = ','.join(pos)

    # create info, index, last name
    info = name + " (" + team + ' - ' + pos + ')'
    index = "_".join([name, team])
    last = re.search('\s(.*)', name).group(1)
    return {
        'Player': player,
        'PlayerInfo': info,
        'Index': index,
        'Name': name,
        'Last': last,
        'Team': team,
        'Positions': pos,
        'Status': status
        }


def get_hitter_table():
    hit = pd.read_html(HITTER_URL)[0]
    hit['Type'] = 'H'
    hit['Link'] = get_links(HITTER_URL, SITE_URL)

    # create projections column
    hit['Projections_H'] = \
        hit['AVG'].map('{:,.3f}'.format).str[1:] + STAT_DELIM + \
        hit['R'].map('{:,.0f}R'.format) + STAT_DELIM + \
        hit['HR'].map('{:,.0f}HR'.format) + STAT_DELIM + \
        hit['RBI'].map('{:,.0f}RBI'.format) + STAT_DELIM + \
        hit['SB'].map('{:,.0f}SB'.format)

    hit = hit.rename(columns={'BB': 'BBh'})
    hit['Projections_P'] = ''
    return hit


def get_pitcher_table():
    pit = pd.read_html(PITCHER_URL)[0]
    pit['Type'] = 'P'
    pit['Link'] = get_links(PITCHER_URL, SITE_URL)

    # create projections column
    pit['K9'] = round(pit['K']/pit['IP']*9, 2)
    pit['Projections_P'] = \
        pit['W'].map('{:,.0f}'.format) + '-' +\
        pit['L'].map('{:,.0f}'.format) + '-' +\
        pit['SV'].map('{:,.0f}SV'.format) + STAT_DELIM +\
        pit['ERA'].map('{:,.2f}'.format) + STAT_DELIM +\
        pit['WHIP'].map('{:,.2f}'.format) + STAT_DELIM +\
        pit['K9'].map('{:,.2f}K9'.format)
    pit['Projections_H'] = ''
    return pit


def get_player_table():
    # get tables
    hit = get_hitter_table()
    pit = get_pitcher_table()

    # append tables
    play = hit.append(pit)

    # get id from link
    play['ID'] = play['Link'].str.extract('projections/([^/]+).php')

    # fix link to player
    play['Link'] = play['Link'].str.replace('/projections/', '/players/')

    # get player info
    play['Info'] = play['Player'].apply(lambda x: get_player_info(x))

    # set index
    play = play.set_index('Player')

    # create df from player info and join
    info = pd.DataFrame(play['Info'].tolist())
    info = info.set_index('Player')
    play = play.join(info)
    play = play.drop(columns='Info')

    # group by and remove duplicates
    play = play.groupby('Index').agg('max')

    # create projections column
    play['Projections'] = (play['Projections_H'] + '\n' + play['Projections_P']).str.strip('\n')

    # drop H and P projections
    play = play.drop(['Projections_H','Projections_P'], axis=1)

    return play


def get_adp_table():
    # get ADP table
    adp = pd.read_html(ADP_URL)[0]

    # rename unnamed columns
    adp = adp.rename(columns={
        'Player  (Team, Position)': 'Player',
        'Notes': 'BestADP',
        'Unnamed: 3': 'WorstADP',
        'Unnamed: 4': 'AvgADP',
        'Unnamed: 5': 'StdADP',
        'Unnamed: 6': 'ADP',
        'Unnamed: 7': 'vsADP',
        'Unnamed: 8': 'Notes'
        })

    # create index column
    adp['Index'] = adp['Player'].apply(lambda x: get_player_info(x)['Index']) 
    adp['Positions'] = adp['Player'].apply(lambda x: get_player_info(x)['Positions']) 
    adp['PlayerInfo'] = adp['Player'].apply(lambda x: get_player_info(x)['PlayerInfo']) 
    adp = adp.drop_duplicates(subset='Index')
    adp = adp.set_index('Index')

    # calcualte vsADP
    adp['vsADP'] = adp['ADP'] - adp['Rank']

    # clean Notes
    adp['Notes'] = adp['Notes'].str.replace('\n', ' ')

    return adp


def get_data_table(csv=None):
    # get tables
    play = get_player_table()
    adp = get_adp_table()

    # join tables
    data = play.join(adp, rsuffix='2')

    # update positions
    pos = adp['Positions']
    info = adp['PlayerInfo']
    data['Positions'].update(pos)
    data['PlayerInfo'].update(info)

    # sort by player rank
    data = data.sort_values(by='Rank')

    # fill null notes with empty string and concat projections
    data['Notes'] = data['Notes'].fillna('')
    data['Description'] = data['Projections'] + '\n' + data['Notes']
    data = data.reset_index()

    # get points rank
    data['PtsRank'] = data['PTS'].rank(ascending=False, method='first')

    # export
    if csv:
        data.to_csv(csv)

    return data


if __name__ == "__main__":
    print(get_data_table().head())
