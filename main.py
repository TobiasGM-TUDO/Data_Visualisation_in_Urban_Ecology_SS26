# folium docs: https://python-visualization.github.io/folium/latest/index.html
import pandas as pd
import folium
import pathlib as pl
import os

## Constants
IBUTTON_PARENT_DIRECTORY = r"Data for students/iButton data"

## Function / Class Definitions
def fix_ibutton_format(raw_data:str):
    raw_data = raw_data.replace("Date/Time,Unit,Value","Date,Time,Unit,Value")
    raw_data
    return raw_data

class IButton:
    def __init__(self, path_to_csv:pl.Path):
        self.path_to_csv = path_to_csv
        self.df = pd.read_csv(path_to_csv, skiprows=18)


## Sensor Data
# Sensor stuff

for dirpath, dirnames, filenames in os.walk(IBUTTON_PARENT_DIRECTORY):
    for filename in filenames:
        file_path = pl.Path(os.path.join(dirpath, filename))
        data = IButton(file_path).df
        print(data)

# Map stuff
sensor_location = pd.read_excel("nestbox_coordinates.xlsx")

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

    kw = {"prefix": "fa", "color": "green", "icon": "arrow-up"}
    icon = folium.Icon(angle=sensor_rot_number, **kw)
    folium.Marker(location=[sensor_lat, sensor_lon], icon=icon, tooltip=str(sensor_rot_text)).add_to(tu_map)

# Save map
tu_map.save('map.html')