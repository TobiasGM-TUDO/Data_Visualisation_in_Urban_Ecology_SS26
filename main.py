# folium docs: https://python-visualization.github.io/folium/latest/index.html
import pandas as pd
import folium

## Sensor Data
sensor_location = pd.read_excel("Data for students/nestbox_coordinates.xlsx")

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