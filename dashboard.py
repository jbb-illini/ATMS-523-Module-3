import pandas as pd
from bokeh.plotting import figure
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import Select, ColumnDataSource, Range1d

# ======================================================================
# 1. Define Station Data and Data Processing Function
# ======================================================================

# Maps city names to their GHCN station IDs.
STATION_DATA = {
    'Chicago, IL': 'USW00094846',
    'New York, NY': 'USW00094728',
    'Los Angeles, CA': 'USW00093134',
    'Miami, FL': 'USW00012839',
    'Denver, CO': 'USW00023062'
}

def get_weather_data(station_id):
    """
    Downloads, cleans, and processes GHCN daily temperature data.
    
    Args:
        station_id (str): The GHCN station ID.

    Returns:
        pd.DataFrame: Processed temperature data, including daily
                      TMAX/TMIN, 1981-2010 "normals", and all-time records.
    """
    url = f"https://noaa-ghcn-pds.s3.amazonaws.com/csv/by_station/{station_id}.csv"
    
    try:
        # Download data, parse 'DATE' as datetime, and set as index.
        df = pd.read_csv(
            url,
            parse_dates=['DATE'],
            dtype={
                'Q_FLAG': 'object', 
                'M_FLAG': 'object'}
        ).set_index('DATE')
    except Exception as e:
        print(f"Error downloading data for station {station_id}: {e}")
        return pd.DataFrame()

    # Filter for TMAX and TMIN.
    df_temp = df[df['ELEMENT'].isin(['TMAX', 'TMIN'])].copy()
    if df_temp.empty:
        return pd.DataFrame()

    # Convert from tenths of a degree Celsius to Celsius.
    df_temp['DATA_VALUE'] = df_temp['DATA_VALUE'] / 10.0
    
    # Extract day of year and year.
    df_temp['day_of_year'] = df_temp.index.dayofyear
    df_temp['year'] = df_temp.index.year
    
    # Pivot to make 'TMAX' and 'TMIN' their own columns.
    df_pivot = df_temp.pivot_table(
        index=['year', 'day_of_year'], 
        columns='ELEMENT', 
        values='DATA_VALUE'
    ).reset_index()

    # Calculate 1981-2010 normals based on the World Meteorological Organization (WMO) standard for climate normals.
    normals = df_pivot[(df_pivot['year'] >= 1981) & (df_pivot['year'] <= 2010)]
    
    # Group and calculate mean for TMAX and TMIN (the "normals").
    averages_by_day = normals.groupby('day_of_year').agg({
        'TMAX': 'mean',
        'TMIN': 'mean'
    }).rename(columns={'TMAX': 'avg_max', 'TMIN': 'avg_min'})

    # Group and find the all-time max and min records.
    records_by_day = df_pivot.groupby('day_of_year').agg({
        'TMAX': 'max',
        'TMIN': 'min'
    }).rename(columns={'TMAX': 'record_max', 'TMIN': 'record_min'})
    
    # Merge all calculated data back.
    df_final = df_pivot.merge(averages_by_day, on='day_of_year')
    df_final = df_final.merge(records_by_day, on='day_of_year')
    
    # Sort for correct plotting order.
    return df_final.sort_values(['year', 'day_of_year'])

# ======================================================================
# 2. Pre-process Data and Set up Widgets
# ======================================================================

# Pre-process and cache all station data.
all_data = {city: get_weather_data(station_id) for city, station_id in STATION_DATA.items()}

# Filter out failed data downloads.
valid_cities = {city: df for city, df in all_data.items() if not df.empty}
cities = sorted(list(valid_cities.keys()))

if not cities:
    # Handle case where all data downloads fail.
    print("Failed to download data for all cities. Please check your network connection.")
    curdoc().add_root(column())
else:
    # Get unique years from the data for the year dropdown.
    years = sorted(valid_cities[cities[0]]['year'].unique())

    # Create widgets.
    city_select = Select(title="City:", options=cities, value=cities[0])
    year_select = Select(title="Year:", options=[str(y) for y in years], value=str(years[-1]))

    # Create the initial data source (ColumnDataSource is key for Bokeh updates).
    initial_city = cities[0]
    initial_year = int(year_select.value)
    initial_df = valid_cities[initial_city][valid_cities[initial_city]['year'] == initial_year]
    source = ColumnDataSource(data=initial_df)

# ======================================================================
# 3. Create the Plot and Callbacks
# ======================================================================

    # Create the main plot figure.
    p = figure(
        height=600,
        width=1200,
        x_axis_label="Day of the Year",
        y_axis_label="Temperature (°C)",
        title=f"Weather Data for {initial_city} in {initial_year}",
        x_range=Range1d(1, 366)
    )

    # Plot all-time record high/low range (lightest blue fill).
    p.varea(x='day_of_year', y1='record_min', y2='record_max', source=source, 
            fill_alpha=0.2, color="#B0C4DE", legend_label="Record")

    # Plot 1981-2010 average high/low range (medium blue fill).
    p.varea(x='day_of_year', y1='avg_min', y2='avg_max', source=source, 
            fill_alpha=0.4, color="#6495ED", legend_label="Average")

    # Plot the actual high and low for the selected year (vertical bars).
    p.vbar(x='day_of_year', top='TMAX', bottom='TMIN', source=source, 
           width=0.8, fill_alpha=0.8, line_alpha=0.0, color="#4682B4", 
           legend_label="Actual")

    # Plot customizations.
    p.x_range.bounds = (1, 366)
    p.legend.location = "top_left"
    p.legend.click_policy = "hide"

    # Callback function to update the plot when a dropdown value changes.
    def update_plot(attrname, old, new):
        selected_city = city_select.value
        selected_year = int(year_select.value)
        
        # Get new data and update the ColumnDataSource.
        new_data = valid_cities[selected_city][valid_cities[selected_city]['year'] == selected_year]
        source.data = new_data
        
        # Update plot title.
        p.title.text = f"Weather Data for {selected_city} in {selected_year}"

    # Attach the callback to widget changes.
    city_select.on_change('value', update_plot)
    year_select.on_change('value', update_plot)

# ======================================================================
# 4. Arrange the Layout and Add to Document
# ======================================================================

    # Arrange widgets and plot.
    controls = column(city_select, year_select)
    layout = row(controls, p)
    # Add the final layout to the Bokeh document.
    curdoc().add_root(layout)