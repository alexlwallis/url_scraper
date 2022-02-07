# Scraping Urls

### Getting Started:

This module uses a few packages, you can download them by running:

`pip install -r scrape/requirements.txt`


## Data Source

### CSV

If you are intending on using a CSV as a data source then please move your CSV file into this module and run this (while in the same directory you cloned this repository):

`python -m scrape csv {filename}`

Where {filename} is the name of the file that was moved to the module, for example:

`python -m scrape csv urls.csv`

No need to include the relative path or absolute path.

### Database

If you are intending on using a PostgreSQL database as a data source then you'll need to supply the database name, the user name and the password to connect to the database. You will also need to supply the column and table name to select the URLs.

`python -m scrape db {db_name} {user} {password} {column} {table}`

Example:

`python -m scrape db urls awallis admin url scraped_urls`

## Data Sink

The Data Sink here is the output.json file and this collects all the data from the URLs.

## Logging

This module uses the logging module in Python's standard library and logging information can be found in the log.log file.

### Assumptions:

- Data is supposed to be outputted in valid JSONlint, so it is outputted in a file instead of a DB
- PostgreSQL is only DB we are interested in using
- When we are given the URL we are only scraping the URL itself, not all of the possible paths for the URL
- Will handle redirects for the inputted URL, but not for redirects for the various links within the inputted URLs html
