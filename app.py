from formatter import get_formatted_table
from datetime import date

if __name__ == "__main__":
    year = date.today().year
    csv = f'data/player-data-{year}.csv'
    raw_csv = f'data/player-data-raw-{year}.csv'
    data = get_formatted_table(year, csv, raw_csv)
