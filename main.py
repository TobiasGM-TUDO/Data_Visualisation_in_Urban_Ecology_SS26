# folium docs: https://python-visualization.github.io/folium/latest/index.html
import pandas as pd
import folium
import pathlib as pl
import os
import io
import re

## Constants
IBUTTON_PARENT_DIRECTORY = r"Data for students/iButton data"

## Function / Class Definitions

class IButton:
    def __init__(self, path_to_csv:pl.Path):
        self.path_to_csv = path_to_csv
        # Determine sensor ID
        id_and_variable = self.path_to_csv.stem.split("_")[0]
        self.id = "".join([character for character in id_and_variable if character.isnumeric()])
        self.variable = "".join([character for character in id_and_variable if not character.isnumeric()])

        # Read the .CSV data
        self.df = pd.read_csv(io.StringIO(self.fix_ibutton_format(path_to_csv)), skiprows=18, decimal=",", delimiter=",")
        # Add sensor ID and variable type (HI, HO, TI, TO) to the data frame
        self.df["Id"] = self.id
        self.df["Variable"] = self.variable

    def fix_ibutton_format(self, path_to_csv:pl.Path):
        with open(path_to_csv) as csv_file:
            csv_file_data_raw = csv_file.readlines()

            # Regex for determining lines with measurement data and the actual measurements with "," as decimal seperator
            regex_measurements = re.compile(r"\d{2}\/\d{2}\/\d{4}")
            regex_values_with_german_decimal = re.compile(r"(\d),(\d)")

            # Loops through each line in the .csv file and replaces commas with dots, if the comma is between 2 numbers
            csv_file_data_out = []
            for i,line in enumerate(csv_file_data_raw):
                if "Date/Time" in line:
                    csv_file_data_out.append(line.replace("Date/Time", "Date,Time").replace("Unit.Value", "Unit,Value").replace("Time.Unit", "Time,Unit"))
                elif regex_measurements.search(line):
                    line_corrected = re.sub(regex_values_with_german_decimal, r"\1.\2", line)
                    csv_file_data_out.append(line_corrected)
                else:
                    csv_file_data_out.append(line)

        return "".join(csv_file_data_out)

def aggregate_ibutton_files(ibutton_parent_directory:pl.Path):
    """Aggregate data from iButton files into one data frame and save to csv"""
    ibutton_data_total = pd.DataFrame(columns=["Id", "Variable", "Date", "Time", "Unit", "Value"])
    for dirpath, dirnames, filenames in os.walk(IBUTTON_PARENT_DIRECTORY):
        for filename in filenames:
            file_path = pl.Path(os.path.join(dirpath, filename))
            ibutton = IButton(file_path)
            ibutton_data = ibutton.df

            if len(ibutton_data.columns) != 6:
                print("Data frame with wrong size!")
                print(file_path)
                print(ibutton_data)

            ibutton_data_total = pd.concat([ibutton_data_total,ibutton_data], ignore_index=True)

    #ibutton_data_total.head(5).to_csv("iButton_measurements_example.csv", index=False)
    ibutton_data_total.to_csv("iButton_measurements.csv", index=False)

def sensor_on_click_popup_html(sensor_metadata):
    return f"""
    <div style="font-family: sans-serif; font-size: 12px;">
        <b>Nestbox {sensor_metadata.nestbox_id}</b><br>
        Type: {sensor_metadata.sensor_type}<br>
        Height: {sensor_metadata.height_cm} cm<br>
        Orientation: {sensor_metadata.orientation}<br>
        Coordinates: {sensor_metadata.lat}, {sensor_metadata.lon}<br>
    </div>
    """

## Sensor Data
# Sensor stuff
#aggregate_ibutton_files(pl.Path(IBUTTON_PARENT_DIRECTORY))
iButton_data = pd.read_csv("iButton_measurements.csv")


# Map stuff
sensor_location = pd.read_excel("nestbox_coordinates.xlsx")
sensor_location["sensor_type"] = sensor_location["sensor_type"].fillna("Only Nest")

## Map Stuff
# Bounding box for relevant map section of TU Dortmund
min_lon, max_lon = 7.40, 7.43
min_lat, max_lat =51.48, 51.5

tu_map = folium.Map(
    max_bounds=True,
    location=[51.4921758, 7.4141904],
    zoom_start=16,
    min_lat=min_lat,
    max_lat=max_lat,
    min_lon=min_lon,
    max_lon=max_lon,
)

## For debugging. Enable when map bounding box should be visible.
# folium.CircleMarker([max_lat, min_lon], tooltip=f"Upper Left Corner {[max_lat, min_lon]}").add_to(tu_map)
# folium.CircleMarker([min_lat, min_lon], tooltip=f"Lower Left Corner {[min_lat, min_lon]}").add_to(tu_map)
# folium.CircleMarker([min_lat, max_lon], tooltip=f"Lower Right Corner {[min_lat, max_lon]}").add_to(tu_map)
# folium.CircleMarker([max_lat, max_lon], tooltip=f"Upper Right Corner {[max_lat, max_lon]}").add_to(tu_map)

# Draw sensors
for sensor in sensor_location.itertuples():
    sensor_rot_number = int(sensor.orientation.replace("N","").replace("E","").replace("S","").replace("W",""))
    sensor_rot_text = sensor.orientation
    sensor_lon = sensor.lon
    sensor_lat = sensor.lat
    sensor_type = sensor.sensor_type
    sensor_id = sensor.nestbox_id

    kw = {"prefix": "fa", "color": "green", "icon": "arrow-up"}
    icon = folium.Icon(angle=sensor_rot_number, **kw)
    tooltip = folium.Tooltip(sensor_on_click_popup_html(sensor), sticky=True)
    folium.Marker(location=[sensor_lat, sensor_lon], icon=icon, tooltip=tooltip).add_to(tu_map)

# Save map
tu_map.save('map.html')