# Scraping Urls

### Getting Started:

This module uses a few packages, you can download them by running:

`pip install -r dc_tagging/requirements.txt`


## Data Source

### CSV

If you are intending on using a CSV as a data source then please move your CSV file into this module and run this (while in the same directory you cloned this repository):

`python -m scrape csv {filename}`

Where {filename} is the name of the file that was moved to the module, for example:

`python -m scrape csv urls.csv`

No need to include the relative path or absolute path.

### Database

If you are intending on using a PostgreSQL database as a data source then you'll need to change the connection on line 18 in __main__.py, you will also likely need to change line 151 in __main__.py to select the correct column in the correct table for your URLs.

When this is all ready you can run:

`python -m scrape db`

## Data Sink

The Data Sink here is the output.json file and this collects all the data from the URLs.

## Logging

This module uses the logging module in Python's standard library and logging information can be found in the log.log file.
