from scraper import get_data_table

COLUMNS = [
    'Name',
    'Team',
    'Positions',
    'Rank',
    'ADP',
    'PlayerInfo',
    'PTS',
    'Projections',
    'Link',
    'Last',
    'Description',
    'Status'
]


def get_formatted_table(year=None, csv=None, raw_csv=None):
    raw = get_data_table(raw_csv)
    maxrank = raw['Rank'].max()
    unr = raw[raw['Rank'].isna()]
    unr['Rank'] = unr['PTS'].rank(ascending=False, method='first')+maxrank
    raw['Rank'][raw['Rank'].isna()] = unr['Rank']
    raw.info()

    data = raw[COLUMNS]
    data = data.sort_values(by='Rank')
    data = data.reset_index()
    data['Rec'] = data.index + 1
    data = data.set_index('Rec')
    data = data.drop(axis=1, columns='index')

    if year:
        data['Year'] = year

    if csv:
        data.to_csv(csv)

    return data
