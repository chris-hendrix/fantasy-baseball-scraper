import pandas as pd
import requests
from bs4 import BeautifulSoup


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


class PlayerScraper:

    SITE_URL = 'https://www.fantasypros.com'
    HITTER_URL = 'https://www.fantasypros.com/mlb/projections/hitters.php?points=E'

    def __init__(self):
        self.n_teams = 10
        self.stat_delimiter = '|'

    def get_hitter_table(self):
        url = PlayerScraper.HITTER_URL
        site = PlayerScraper.SITE_URL
        print(url, site)
        hit = pd.read_html(url)[0]
        hit['Type'] = 'H'
        hit['Link'] = get_links(url, site)

        # create projections column
        delim = self.stat_delimiter
        hit['Projections_H'] = \
            hit['AVG'].map('{:,.3f}'.format).str[1:] + delim + \
            hit['R'].map('{:,.0f}R'.format) + delim + \
            hit['HR'].map('{:,.0f}HR'.format) + delim + \
            hit['RBI'].map('{:,.0f}RBI'.format) + delim + \
            hit['SB'].map('{:,.0f}SB'.format)

        hit = hit.rename(columns={'BB': 'BBh'})
        hit['Projections_P'] = ''
        return hit


if __name__ == "__main__":
    ps = PlayerScraper()
    print(ps.get_hitter_table().head())
