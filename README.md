# Project README: Weather Dashboard

This project is an interactive web application that visualizes historical weather data for several major cities. The dashboard is built using **Bokeh** for plotting and **pandas** for data processing. It allows users to explore temperature trends, including daily averages and all-time records, for a selected city and year.

---

### Features

* **Interactive Plotting**: Displays daily temperature data, including all-time record highs/lows, 1981-2010 averages, and actual daily temperatures for the selected year.
* **Data from NOAA**: The application fetches Global Historical Climatology Network Daily (GHCN-D) data directly from an Amazon Web Services S3 bucket. URL: https://registry.opendata.aws/noaa-ghcn/
* **User Controls**: Dropdown menus allow users to select a specific city and year.
* **Leap Year Handling**: The code ensures that all data for February 29th is properly grouped and calculated with other leap year data.

---

### How It Works

This application (`dashboard.py`) is a Bokeh server app. It follows these main steps:

1.  **Data Acquisition**: The `get_weather_data` function downloads and processes historical temperature data for a given weather station.
2.  **Data Processing**: Using pandas, the function cleans the data and calculates three key temperature metrics for each day of the year:
    * **Record**: The all-time highest and lowest temperatures ever recorded on that specific day.
    * **Average**: The average high and low temperatures for that day, based on the 1981-2010 "normal" period.
    * **Actual**: The actual high and low temperatures for the user-selected year.
3.  **Visualization**: The processed data is loaded into a Bokeh via `ColumnDataSource`, which links the data to the plot's shaded areas or "glyphs" (`varea` for the shaded ranges and `vbar` for the actual temperatures).
4.  **Interaction**: The plot and a set of widgets (city and year dropdowns) are arranged within the layout. The graphs updaed automatically with the help of callback methods inherent to Bokeh and through the "update plot function."

---

### Requirements

To run this application, you need to install the following Python libraries:
* `pandas`
* `bokeh`

You can install them using `pip`:
```bash
pip install pandas bokeh