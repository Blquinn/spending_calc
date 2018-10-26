from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd
import argparse
import csv
import jinja2


templateLoader = jinja2.FileSystemLoader('./templates')
templateEnv = jinja2.Environment(loader=templateLoader)


def main(args):
    generate_chase_stmt(args.chase_stmt_path, args.chase_stmt_out)


def generate_chase_stmt(path, output):
    with open(path, 'r') as f:
        reader = csv.DictReader(f, skipinitialspace=True, delimiter=',')
        stmt_list = [{k: v for k, v in row.items()} for row in reader]

    df = pd.DataFrame(stmt_list)
    df['Amount'] = df['Amount'].dropna()
    df['Amount'] = pd.to_numeric(df['Amount'])
    df['Posting Date'] = pd.to_datetime(df['Posting Date'])
    df.set_index(df['Posting Date'], inplace=True)

    df_creds = df.loc[df['Amount'] < 0]

    # TODO: remove the first month if account was opened midway through month.
    # This would throw off the average burn, if there was a partial month.

    # Beggining of month, 1 year ago
    beginning_of_month = date.today().replace(day=1)
    end_of_prev = beginning_of_month - relativedelta(days=1)
    n_months_ago = (beginning_of_month - relativedelta(years=1))
    df_year = df_creds[
        (df_creds.index > n_months_ago.isoformat()) &
        (df_creds.index <= end_of_prev.isoformat())
        ]

    # Get last 12 months only
    monthly = df_year.groupby(pd.Grouper(freq='M')).sum()
    monthly_list = [
        {
            'date': val.name.strftime('%B %Y'),
            'spend': -round(val.Amount, 2),
        }
        for idx, val in monthly.iterrows()
    ]

    avg_burn = -round(monthly.mean().iloc[0], 2)
    template = templateEnv.get_template('chase_stmt.html.j2')
    output_html = template.render({
        'monthly_data': monthly_list,
        'average_burn': avg_burn,
    })
    if not output:
        path = './out/chase_stmt.html'
        print(f'Writing statement to {path}')
        with open(path, 'w') as f:
            f.write(output_html)
    else:
        with open(output, 'w') as f:
            f.write(output_html)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate finances.')
    parser.add_argument('--chase', dest='chase_stmt_path', type=str,
                        help='Chase account statement (1 Yr)', required=True)
    parser.add_argument('--chase-out', dest='chase_stmt_out', type=str,
                        help='Chase account statement html output path',
                        required=False)
    args = parser.parse_args()
    main(args)
