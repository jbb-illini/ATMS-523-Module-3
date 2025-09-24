import pandas as pd
from bokeh.plotting import figure
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import Select, ColumnDataSource, Range1d

# ======================================================================
# 1. Define Station Data and Data Processing Function
# ======================================================================

# A dictionary mapping user-friendly city names to their respective GHCN station IDs.
# This makes the dashboard user-friendly by allowing selection by city name.
STATION_DATA = {
    'Chicago, IL': 'USW00094846',
    'New York, NY': 'USW00094728',
    'Los Angeles, CA': 'USW00093134',
    'Miami, FL': 'USW00012839',
    'Denver, CO': 'USW00023062'
}

def get_weather_data(station_id):
    """
    Downloads, cleans, and processes GHCN daily temperature data for a specified station.
    This function performs all the heavy lifting of data preparation for the dashboard.
    
    Args:
        station_id (str): The GHCN station ID.

    Returns:
        pd.DataFrame: A DataFrame with processed temperature data, including daily
                      TMAX/TMIN, 1981-2010 "normals", and all-time records.
    """
    # Construct the direct HTTP URL for the station's data in CSV format.
    url = f"https://noaa-ghcn-pds.s3.amazonaws.com/csv/by_station/{station_id}.csv"
    
    try:
        # Download the CSV and parse the 'DATE' column as datetime objects.
        # Set the 'DATE' column as the DataFrame's index.
        df = pd.read_csv(
            url,
            parse_dates=['DATE'],
            dtype={
                'Q_FLAG': 'object', 
                'M_FLAG': 'object'}
        ).set_index('DATE')
    except Exception as e:
        # Handle cases where the data for a station cannot be downloaded.
        print(f"Error downloading data for station {station_id}: {e}")
        return pd.DataFrame()

    # Filter the data to only include daily maximum (TMAX) and minimum (TMIN) temperatures.
    df_temp = df[df['ELEMENT'].isin(['TMAX', 'TMIN'])].copy()
    if df_temp.empty:
        # Return an empty DataFrame if no TMAX or TMIN data is found.
        return pd.DataFrame()

    # The original data is in tenths of a degree Celsius; this converts it to degrees Celsius.
    df_temp['DATA_VALUE'] = df_temp['DATA_VALUE'] / 10.0
    
    # Calculate the day of the year and the year from the datetime index.
    # This is crucial for grouping and calculating daily records and normals.
    df_temp['day_of_year'] = df_temp.index.dayofyear
    df_temp['year'] = df_temp.index.year
    
    # Use a pivot table to reshape the data, making 'TMAX' and 'TMIN' their own columns.
    df_pivot = df_temp.pivot_table(
        index=['year', 'day_of_year'], 
        columns='ELEMENT', 
        values='DATA_VALUE'
    )
    df_pivot = df_pivot.reset_index()

    # Calculate 1981-2010 normals and all-time records.
    # First, filter the pivoted data to only include the normal period.
    normals = df_pivot[(df_pivot['year'] >= 1981) & (df_pivot['year'] <= 2010)]
    
    # Group the normals data by `day_of_year` and calculate the mean for TMAX and TMIN.
    # The .agg() function allows for multiple aggregations at once.
    normals_by_day = normals.groupby('day_of_year').agg({
        'TMAX': 'mean',
        'TMIN': 'mean'
    }).rename(columns={'TMAX': 'avg_max', 'TMIN': 'avg_min'})

    # Group the entire dataset by `day_of_year` and find the all-time max and min.
    records_by_day = df_pivot.groupby('day_of_year').agg({
        'TMAX': 'max',
        'TMIN': 'min'
    }).rename(columns={'TMAX': 'record_max', 'TMIN': 'record_min'})
    
    # Merge all the calculated data (normals and records) back into the main DataFrame.
    df_final = df_pivot.merge(normals_by_day, on='day_of_year')
    df_final = df_final.merge(records_by_day, on='day_of_year')
    
    # Sort the data for proper plotting order.
    return df_final.sort_values(['year', 'day_of_year'])

# ======================================================================
# 2. Pre-process Data and Set up Widgets
# ======================================================================

# Pre-process and cache all station data at the start.
# This prevents the need to re-download data every time a user changes the selection.
all_data = {city: get_weather_data(station_id) for city, station_id in STATION_DATA.items()}

# Filter out any cities where the data download failed.
valid_cities = {city: df for city, df in all_data.items() if not df.empty}
cities = sorted(list(valid_cities.keys()))

if not cities:
    # If no data could be downloaded, display an error message and exit.
    print("Failed to download data for all cities. Please check your network connection.")
    curdoc().add_root(column())
else:
    # Get a list of unique years from the first valid city's data for the year dropdown.
    years = sorted(valid_cities[cities[0]]['year'].unique())

    # Create the interactive widgets for the dashboard.
    city_select = Select(title="City:", options=cities, value=cities[0])
    year_select = Select(title="Year:", options=[str(y) for y in years], value=str(years[-1]))

    # Create the initial data source for the plot.
    # Bokeh's plots will reference this ColumnDataSource. Updating the data within this source
    # is the key to creating an interactive plot that changes based on user input.
    initial_city = cities[0]
    initial_year = int(year_select.value)
    initial_df = valid_cities[initial_city][valid_cities[initial_city]['year'] == initial_year]
    source = ColumnDataSource(data=initial_df)

# ======================================================================
# 3. Create the Plot and Callbacks
# ======================================================================

    # Create the main plot figure.
    # We set the `x_range` to a fixed 1-366 to always show a full year,
    # regardless of the data for the selected year.
    p = figure(
        height=600,
        width=1200,
        x_axis_label="Day of the Year",
        y_axis_label="Temperature (°C)",
        title=f"Weather Data for {initial_city} in {initial_year}",
        x_range=Range1d(1, 366)
    )

    # Plot the all-time record high and low ranges using the varea glyph.
    # This creates the lightest blue shaded area in the background.
    p.varea(x='day_of_year', y1='record_min', y2='record_max', source=source, 
            fill_alpha=0.2, color="#B0C4DE", legend_label="Record")

    # Plot the 1981-2010 normal high and low averages using the varea glyph.
    # This creates the medium blue shaded area.
    p.varea(x='day_of_year', y1='avg_min', y2='avg_max', source=source, 
            fill_alpha=0.4, color="#6495ED", legend_label="Average")

    # Plot the actual high and low for the selected year as vertical bars.
    p.vbar(x='day_of_year', top='TMAX', bottom='TMIN', source=source, 
           width=0.8, fill_alpha=0.8, line_alpha=0.0, color="#4682B4", 
           legend_label="Actual")

    # Final plot customizations:
    p.x_range.bounds = (1, 366)       # Ensure the x-axis always spans the full year.
    p.legend.location = "top_left"    # Move the legend to the top-left corner.
    p.legend.click_policy = "hide"    # Allow users to hide/show plot elements by clicking the legend.

    # This function is the "callback" that updates the plot. It is triggered by
    # a change in the dropdown widgets.
    def update_plot(attrname, old, new):
        selected_city = city_select.value
        selected_year = int(year_select.value)
        
        # Get the new data based on the selected city and year.
        new_data = valid_cities[selected_city][valid_cities[selected_city]['year'] == selected_year]
        # Update the ColumnDataSource's data. Bokeh automatically refreshes the plot.
        source.data = new_data
        
        # Update the title of the plot to reflect the current selection.
        p.title.text = f"Weather Data for {selected_city} in {selected_year}"

    # Attach the callback function to the widgets' `on_change` events.
    # This means the `update_plot` function will run whenever a user changes
    # the value of either dropdown menu.
    city_select.on_change('value', update_plot)
    year_select.on_change('value', update_plot)

# ======================================================================
# 4. Arrange the Layout and Add to Document
# ======================================================================

    # Arrange the widgets in a column on the left side of the dashboard.
    controls = column(city_select, year_select)
    # Arrange the controls and the plot side-by-side in a row.
    layout = row(controls, p)
    # Add the final layout to the Bokeh document, which is served by the Bokeh server.
    curdoc().add_root(layout)