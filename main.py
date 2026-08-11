# folium docs: https://python-visualization.github.io/folium/latest/index.html
import pandas as pd
import numpy as np
import folium
import pathlib as pl
import os
import io
import re
from folium.plugins import FloatImage, GroupedLayerControl, MeasureControl, MousePosition, Search, TagFilterButton
import io
from matplotlib.figure import Figure
from matplotlib.dates import AutoDateLocator, DateFormatter
from matplotlib.ticker import MaxNLocator
from nest_icons import nest_icon, add_nest_css, SPECIES # <- AI
from badge_toggle import BadgeToggle # <- AI
import base64 # For favicon


## Constants
IBUTTON_PARENT_DIRECTORY = r"Data for students/iButton data"
DAY_START, DAY_END = 10, 17
SPECIES_NAMES = {"GT": "Great Tit", "BT": "Blue Tit"}
READINGS = {
    "iButton": (
        "iButton readings",
        (("T<sub>in</sub> [°C]",   "TI"),
         ("T<sub>out</sub> [°C]",  "TO"),
         ("RH<sub>in</sub> [%]",   "HI"),
         ("RH<sub>out</sub> [%]",  "HO")),
    ),
    # "Intelligent": (
    #     "Intelligent sensor readings",
    #     (("T<sub>in</sub> [°C]",  "T"),
    #      ("RH<sub>in</sub> [%]",  "H"),
    #      ("SPL [dB]",             "S"),
    #      ("E<sub>v</sub> [lx]",   "L")),
    # ),
}
## Function / Class Definitions

class Nestbox:
    def __init__(self, metadata, sensor_data=None):
        self.Year = metadata.Year
        self.ID = metadata.ID
        self.Type = metadata.Type
        self.Lat = metadata.Lat
        self.Lon = metadata.Lon
        self.Species_1 = metadata.Species_1
        self.Species_2 = metadata.Species_2
        self.Height = metadata.Height
        self.Orientation = metadata.Orientation
        self.Eggs = metadata.Eggs
        self.Chicks = metadata.Chicks
        self.Deaths = metadata.Deaths
        self.sensor_data = sensor_data
        self.daytime_readings = None
        self.nighttime_readings = None
        self.daytime_means = None
        self.daytime_max = None
        self.daytime_min = None
        self.daytime_graphs = None
        self.nighttime_means = None
        self.nighttime_max = None
        self.nighttime_min = None
        self.nighttime_graphs = None
        if sensor_data is not None:
            is_daytime = sensor_data["Timestamp"].dt.hour.between(DAY_START, DAY_END)
            self.daytime_readings = self.sensor_data[is_daytime].groupby("Variable")
            self.nighttime_readings = self.sensor_data[~is_daytime].groupby("Variable")
            self.aggregate_sensor_data()
        self.tooltip = self._tooltip()
        self.popup = self._popup()

    def aggregate_sensor_data(self):
        daytime = self.daytime_readings
        self.daytime_min = daytime["Value"].min()
        self.daytime_means = daytime["Value"].mean()
        self.daytime_max = daytime["Value"].max()
        nighttime = self.nighttime_readings
        self.nighttime_min = nighttime["Value"].min()
        self.nighttime_means = nighttime["Value"].mean()
        self.nighttime_max = nighttime["Value"].max()

    def _species_label(self):
        """"Great Tit", or "1st Great Tit, 2nd Blue Tit" when a second brood was recorded."""

        def name(code):
            if code is None or code != code:
                return None
            return SPECIES_NAMES.get(code, code)

        first, second = name(self.Species_1), name(self.Species_2)

        if first is None:
            return "Empty"
        if second is None:
            return first
        return f"1st {first}, 2nd {second}"

    def _meta_table(self):
        """The rows that exist for every nestbox, whatever sensors it carries."""
        rows = (
            ("Type", self.Type),
            ("Species", self._species_label()),
            ("Height", f"{format_number(self.Height, 0)} cm"),
            ("Orientation", f"{format_number(self.Orientation, 0)}°"),
            ("Eggs / Chicks / Deaths",
             " / ".join(format_number(value, 0)
                        for value in (self.Eggs, self.Chicks, self.Deaths))),
        )
        cells = "".join(f"<tr><th>{label}</th><td>{value}</td></tr>" for label, value in rows)
        return f'<table class="nb-meta">{cells}</table>'

    def _readings_table(self):
        """The sensor block. Empty string for nestbox types that carry no sensors."""
        if self.Type not in READINGS or self.daytime_means is None:
            return ""

        caption, row_spec = READINGS[self.Type]
        columns = (self.daytime_min, self.daytime_means, self.daytime_max,
                   self.nighttime_min, self.nighttime_means, self.nighttime_max)
        FIRST_NIGHT_COLUMN = 3

        rows = ""
        for label, variable in row_spec:
            cells = ""
            for index, series in enumerate(columns):
                divider = ' class="nb-night"' if index == FIRST_NIGHT_COLUMN else ""
                cells += f"<td{divider}>{format_number(series.get(variable))}</td>"
            rows += f"<tr><td>{label}</td>{cells}</tr>"

        return f"""
            <p class="nb-caption">{caption}</p>
            <table class="nb-readings">
                <tr class="nb-group">
                    <th></th><th colspan="3">Day ({DAY_START}&ndash;{DAY_END} h)</th>
                    <th colspan="3" class="nb-night">Night</th>
                </tr>
                <tr>
                    <th></th><th>Min</th><th>&empty;</th><th>Max</th>
                    <th class="nb-night">Min</th><th>&empty;</th><th>Max</th>
                </tr>
                {rows}
            </table>"""

    def _tooltip(self):
        if self.sensor_data is not None:
            pop_up_hint = "-> Click for more information!"
        else:
            pop_up_hint = ""
        return f"""
            <div class="nb-tip">
                <div class="nb-head">Nestbox {self.ID}</div>
                {self._meta_table()}
                {self._readings_table()}
                {pop_up_hint}
            </div>"""

    def _popup(self):
        if self.sensor_data is None: return None

        if "TI" in self.daytime_readings.groups:
            ti_day = (self.daytime_readings.get_group("TI").resample("D", on="Timestamp")["Value"].mean().rolling(3, center=True, min_periods=1).mean())
        else:
            ti_day = None
        if "TO" in self.daytime_readings.groups:
            to_day = (self.daytime_readings.get_group("TO").resample("D", on="Timestamp")["Value"].mean().rolling(3, center=True, min_periods=1).mean())
        else:
            to_day = None
        if "TI" in self.nighttime_readings.groups:
            ti_night = (self.nighttime_readings.get_group("TI").resample("D", on="Timestamp")["Value"].mean().rolling(3, center=True, min_periods=1).mean())
        else:
            ti_night = None
        if "TO" in self.nighttime_readings.groups:
            to_night = (self.nighttime_readings.get_group("TO").resample("D", on="Timestamp")["Value"].mean().rolling(3, center=True, min_periods=1).mean())
        else:
            to_night = None
        if "HI" in self.daytime_readings.groups:
            hi_day = (self.daytime_readings.get_group("HI").resample("D", on="Timestamp")["Value"].mean().rolling(3, center=True, min_periods=1).mean())
        else:
            hi_day = None
        if "HO" in self.daytime_readings.groups:
            ho_day = (self.daytime_readings.get_group("HO").resample("D", on="Timestamp")["Value"].mean().rolling(3, center=True, min_periods=1).mean())
        else:
            ho_day = None
        if "HI" in self.nighttime_readings.groups:
            hi_night = (self.nighttime_readings.get_group("HI").resample("D", on="Timestamp")["Value"].mean().rolling(3, center=True, min_periods=1).mean())
        else:
            hi_night = None
        if "HO" in self.nighttime_readings.groups:
            ho_night = (self.nighttime_readings.get_group("HO").resample("D", on="Timestamp")["Value"].mean().rolling(3, center=True, min_periods=1).mean())
        else:
            ho_night = None

        INSIDE, OUTSIDE = "#D55E00", "#0072B2"
        DAY, NIGHT = ("-", 1.3), ((0, (4, 2)), 1.3)

        t_plot = self._plot_to_svg(
            [
                {"series": ti_day, "label": "Inside Day", "format": DAY, "color": INSIDE},
                {"series": ti_night, "label": "Inside Night", "format": NIGHT, "color": INSIDE},
                {"series": to_day, "label": "Outside Day", "format": DAY, "color": OUTSIDE},
                {"series": to_night, "label": "Outside Night", "format": NIGHT, "color": OUTSIDE},
                ],
                unit="°C",
                title="Temperature",
                xlabel_enabled=False)
        h_plot = self._plot_to_svg(
            [
                {"series": hi_day, "label": "Inside Day", "format": DAY, "color": INSIDE},
                {"series": hi_night, "label": "Inside Night", "format": NIGHT, "color": INSIDE},
                {"series": ho_day, "label": "Outside Day", "format": DAY, "color": OUTSIDE},
                {"series": ho_night, "label": "Outside Night", "format": NIGHT, "color": OUTSIDE},
                ],
                unit="%",
                title="Humidity",
                legend=False,
                xlabel_enabled=True)


        popup_html = f"""<div class="nb-head">Nestbox {self.ID}</div>
                        {t_plot} {h_plot}"""
        return popup_html

    def _plot_to_svg(self, data, title=None, unit="", legend=True, xlabel_enabled=True):
        """Render a small line plot and return it as an inline-ready SVG string."""
        figure = Figure(figsize=(4, 2), dpi=100)
        axes = figure.subplots()
        for plot_data in data:
            if plot_data["series"] is not None:
                linestyle, linewidth = plot_data["format"]
                axes.plot(plot_data["series"].index, plot_data["series"].values, linestyle=linestyle, linewidth=linewidth, color=plot_data["color"], label=plot_data["label"])

        #axes.set_title(title, fontsize=9)
        axes.xaxis.set_major_locator(AutoDateLocator(maxticks=5, minticks=5))
        axes.xaxis.set_major_formatter(DateFormatter("%d %b"))
        axes.tick_params(axis="x", labelsize=7, labelrotation=30)
        for label in axes.get_xticklabels():
            label.set_horizontalalignment("right")
            label.set_rotation_mode("anchor")
        if xlabel_enabled:
            axes.set_xlabel(f"Date ({self.Year})", fontsize=7)

        axes.set_ylabel(f"{title} / {unit}", fontsize=7)
        axes.yaxis.set_major_locator(MaxNLocator(nbins=5))

        if legend:
            axes.legend(fontsize=6, frameon=False, ncols=2, loc="upper center", bbox_to_anchor=(0.5, 1.28), handlelength=2.4, columnspacing=1.4)

        buffer = io.StringIO()
        figure.savefig(buffer, format="svg", bbox_inches="tight")

        svg = buffer.getvalue()
        return svg[svg.index("<svg"):]

class IbuttonFile:
    def __init__(self, path_to_csv:pl.Path):
        self.path_to_csv = path_to_csv
        # Determine sensor ID
        id_and_variable = self.path_to_csv.stem.split("_")
        if len(id_and_variable) <= 2:
            id_and_variable = id_and_variable[0].upper()
        else:
            id_and_variable = "".join([substring for substring in id_and_variable if substring.lower() != ".csv"]).replace("inside", "I").replace("outside", "O").upper()
            if len(id_and_variable) > 4:
                if "-" in id_and_variable:
                    id_and_variable = id_and_variable.split("-")[0]
                    id_and_variable = id_and_variable[:-8]
        if " " in self.path_to_csv.stem:
            id_and_variable = id_and_variable.split(" ")
            id_and_variable = [substring for substring in id_and_variable if "." not in substring]
            id_and_variable = "".join(id_and_variable)

        # Alert entries with empty variable
        if len(id_and_variable) < 3 or  len(id_and_variable) > 4:
            print(f"Unparsable ID/Variable: {self.path_to_csv}", id_and_variable)
            self.id = None
            self.variable = None
            self.df = None
        else:
            self.id = "".join([character for character in id_and_variable if character.isnumeric()])
            # Correct variable order and save it alongside the id
            self.variable = "".join([character for character in id_and_variable if not character.isnumeric()])
            self.variable = self.variable.replace("IT", "TI").replace("OT", "TO").replace("IH", "HI").replace("OH", "HO")

            # Read the .CSV data
            self.df = pd.read_csv(io.StringIO(self.fix_ibutton_format(path_to_csv)), skiprows=18, decimal=",", delimiter=",")

            # Cross-check the file name derived unit with the unit of actual readings and correct if needed
            unit_file_content = self.df.iloc[0].Unit.replace("C", "T").replace("%RH", "H")
            if unit_file_content not in self.variable:
                print(f"Unit mismatch for file '{self.path_to_csv}' (ID: {self.id}! The file name reports {self.variable} and the content {unit_file_content}.")
                if "I" in self.path_to_csv.stem:
                    self.variable = unit_file_content + "I"
                elif "O" in self.path_to_csv.stem:
                    self.variable = unit_file_content + "O"
                else:
                    self.variable = unit_file_content + "X"
                print(f"The new variable will be '{self.variable}'")

            # Add sensor ID and variable type (HI, HO, TI, TO) to the data frame
            self.df["ID"] = self.id
            self.df["Variable"] = self.variable


    def fix_ibutton_format(self, path_to_csv:pl.Path):
        with open(path_to_csv) as csv_file:
            csv_file_data_raw = csv_file.readlines()

            # Regex for determining lines with measurement data and the actual measurements with "," as decimal seperator
            regex_measurements = re.compile(r"\d{2}\/\d{2}\/\d{4}")
            regex_values_with_german_decimal = re.compile(r"(\d),(\d)")

            # Loops through each line in the .csv file and replaces commas with dots, if the comma is between 2 numbers. Also fixed wrong seperator between Unit and value in some cases.
            csv_file_data_out = []
            for i,line in enumerate(csv_file_data_raw):
                if "Date/Time" in line:
                    csv_file_data_out.append(line.replace("Date/Time", "Date,Time").replace("Unit.Value", "Unit,Value").replace("Time.Unit", "Time,Unit"))
                elif regex_measurements.search(line):
                    line_corrected = re.sub(regex_values_with_german_decimal, r"\1.\2", line).replace("C.", "C,").replace("%RH.", "%RH,")
                    csv_file_data_out.append(line_corrected)
                else:
                    csv_file_data_out.append(line)

        return "".join(csv_file_data_out)

def aggregate_ibutton_files(ibutton_parent_directory:pl.Path):
    """Aggregate data from iButton files into one data frame and save to csv"""
    ibutton_data_total = pd.DataFrame(columns=["ID", "Variable", "Date", "Time", "Unit", "Value"])
    for dirpath, dirnames, filenames in os.walk(IBUTTON_PARENT_DIRECTORY):
        for filename in filenames:
            file_path = pl.Path(os.path.join(dirpath, filename))
            ibutton = IbuttonFile(file_path)
            ibutton_data = ibutton.df
            if not ibutton.id: continue

            if len(ibutton_data.columns) != 6:
                print("Data frame with wrong size!")
                print(file_path)
                print(ibutton_data)

            ibutton_data_total = pd.concat([ibutton_data_total,ibutton_data], ignore_index=True)


    # Create timestamps from date and time
    ibutton_data_total["Timestamp"] = pd.to_datetime(ibutton_data_total["Date"] + ibutton_data_total["Time"], format="%d/%m/%Y %H:%M:%S", errors="coerce")

    # Drops duplicates from mistakenly duplicated files and saves the data fram to csv
    ibutton_data_total = ibutton_data_total.drop_duplicates(subset=["ID", "Variable", "Timestamp"])
    ibutton_data_total.to_csv("iButton_measurements.csv", index=False)

def aggregate_nestbox_data(nestbox_data_parent_dir:pl.Path):
    """
    Creates a .csv file containing all the important nestbox data from 2024-2026

    :param nestbox_data_parent_dir:
    :return: nothing
    """
    excel_paths = list(nestbox_data_parent_dir.rglob(f"*[Nn]est*[Cc]hecks*.xlsx"))

    df_target = pd.DataFrame(columns=["Year", "ID", "Type", "Lat", "Lon", "Species_1", "Species_2", "Height", "Orientation", "Eggs", "Chicks", "Deaths"])
    for file_path in excel_paths:
        data_year = str(file_path.stem).split(" ")[0]
        # Check if the year could be extracted from the name
        if "~" in file_path.stem: continue #<- Skips temp. copies of opened Excel files
        if not data_year.isnumeric() and type(data_year) != int:
            print(f"Year for file {file_path} could not be determined! Skipping...")
            continue

        df_source = pd.read_excel(file_path, index_col=False, header=None)
        df_target_per_year = pd.DataFrame(columns=df_target.columns)

        if int(data_year) == 2024:
            df_header = df_source.drop(range(13, len(df_source))).transpose()
            df_header = df_header.rename(columns=df_header.iloc[0]).drop(df_header.index[0]).head(73)

            df_target_per_year["ID"] = df_header["New Nest ID"]
            df_target_per_year["Species_1"] = df_header["Species"]
            df_target_per_year["Species_2"] = df_header["Second brood"]
            df_target_per_year["Height"] = df_header["Height (cm)"]
            df_target_per_year["Orientation"] = df_header["Orientation"]


            # Drops all rows that don't have an ID (1 nestbox in the original dataset for 2024)
            df_target_per_year = df_target_per_year.dropna(subset=["ID"])

            # Sorts the rows by ID
            df_target_per_year = df_target_per_year.sort_values(by=["ID"], ascending=True)

            # Sets the nest type
            df_target_per_year["Type"] = df_header["iButton"].str.replace("x", "iButton").fillna("Nest")

            df_nest_data = df_source.drop(range(0, 13)).rename(columns=df_source.iloc[11])
            for ID in df_nest_data.columns:
                if "Nest ID" in str(ID): continue
                if not ID or str(ID).lower() == "nan": continue
                nest_data = df_nest_data[ID]

                # Determines the max. amount of chicks found in a nest
                chicks = nest_data[nest_data.str.contains("Chick", case=False, na=False)].tolist()
                if not chicks:
                    chicks = 0
                else:
                    CHICK_RE = re.compile(r"(\d+)\s*chicks?\b", re.IGNORECASE)
                    chicks = [int(n) for entry in chicks for n in CHICK_RE.findall(str(entry))]
                    if not chicks:
                        chicks = np.nan
                    else:
                        chicks = max(chicks)
                df_target_per_year.loc[df_target_per_year["ID"] == ID, "Chicks"] = chicks

                # Determines the max. amount of eggs found in a nest
                eggs = nest_data[nest_data.str.contains("CC|CU|WU", case=False, na=False, regex=True)].tolist()
                if not eggs:
                    eggs = 0
                else:
                    EGG_RE = re.compile(r"(\d+)\s*(?:CC|CU|WU)\b", re.IGNORECASE)
                    eggs = [int(n) for entry in nest_data.dropna() for n in EGG_RE.findall(str(entry))]
                    if not eggs:
                        eggs = np.nan
                    else:
                        eggs = max(eggs)
                df_target_per_year.loc[df_target_per_year["ID"] == ID, "Eggs"] = eggs

                # Determines the max. amount od deaths
                deaths = nest_data[nest_data.str.contains(r"dead\b(?!\s*eggs?\b)", case=False, na=False, regex=True)].tolist()
                if not deaths:
                    deaths = 0
                else:
                    DEAD_EGG_RE = re.compile(r"dead\s*eggs?", re.IGNORECASE)
                    DEAD_RE = re.compile(r"(\d+)\s*(?:dead\b|chicks?\s+dead\b)", re.IGNORECASE)

                    deaths = [int(n) for entry in deaths for n in DEAD_RE.findall(str(entry))]
                    if not deaths:
                        deaths = np.nan
                    else:
                        deaths = max(deaths)
                df_target_per_year.loc[df_target_per_year["ID"] == ID, "Deaths"] = deaths

        elif 2025 <= int(data_year) <= 2026:
            df_header = df_source.drop(range(7, len(df_source))).transpose()
            df_header = df_header.rename(columns=df_header.iloc[0]).drop(df_header.index[0])

            df_target_per_year["ID"] = df_header["Date/NestID"]
            df_target_per_year["Species_1"] = df_header["Species"]
            if int(data_year) == 2026:
                df_target_per_year["Species_2"] = df_header["Species 2nd brood"]
            else:
                df_target_per_year["Species_2"] = None
            df_target_per_year["Height"] = df_header["Height (cm)"]
            df_target_per_year["Orientation"] = df_header["Orientation"]

            # Sets the nest type
            df_target_per_year["Type"] = df_header["iButton"].str.replace("x", "iButton").fillna("Nest")
            df_target_per_year.loc[df_target_per_year["ID"].str.startswith("S", na=False), "Type"] = "Intelligent"

            df_nest_data = df_source.drop(range(0, 7)).rename(columns=df_source.iloc[6])
            for ID in df_nest_data.columns:
                if "Date" in str(ID): continue
                nest_data = df_nest_data[ID]

                # Determines the max. amount of chicks found in a nest
                chicks = nest_data[nest_data.str.contains("Chick", case=False, na=False)].tolist()
                if not chicks:
                    chicks = 0
                else:
                    CHICK_RE = re.compile(r"(\d+)\s*chicks?\b", re.IGNORECASE)
                    chicks = [int(n) for entry in chicks for n in CHICK_RE.findall(str(entry))]
                    if not chicks:
                        chicks = np.nan
                    else:
                        chicks = max(chicks)
                df_target_per_year.loc[df_target_per_year["ID"] == ID, "Chicks"] = chicks

                # Determines the max. amount of eggs found in a nest
                eggs = nest_data[nest_data.str.contains("CC|CU|WU", case=False, na=False, regex=True)].tolist()
                if not eggs:
                    eggs = 0
                else:
                    EGG_RE = re.compile(r"(\d+)\s*(?:CC|CU|WU)\b", re.IGNORECASE)
                    eggs = [int(n) for entry in eggs for n in EGG_RE.findall(str(entry))]
                    if not eggs:
                        eggs = np.nan
                    else:
                        eggs = max(eggs)
                df_target_per_year.loc[df_target_per_year["ID"] == ID, "Eggs"] = eggs

                # Determines the max. amount od deaths
                deaths = nest_data[nest_data.str.contains(r"dead\b(?!\s*eggs?\b)", case=False, na=False, regex=True)].tolist()
                if not deaths:
                    deaths = 0
                else:
                    DEAD_EGG_RE = re.compile(r"dead\s*eggs?", re.IGNORECASE)
                    DEAD_RE = re.compile(r"(\d+)\s*(?:dead\b|chicks?\s+dead\b)", re.IGNORECASE)

                    deaths = [int(n) for entry in deaths for n in DEAD_RE.findall(str(entry))]
                    if not deaths:
                        deaths = np.nan
                    else:
                        deaths = max(deaths)
                df_target_per_year.loc[df_target_per_year["ID"] == ID, "Deaths"] = deaths

        df_target_per_year["Year"] = data_year
        df_target = pd.concat([df_target, df_target_per_year], ignore_index=True)

    # Clean up species column
    df_target["Species_1"] = (
        df_target["Species_1"]
        .str.strip()
        .replace({r"\?": "", r"\s*\(aggressiv\)": ""}, regex=True)  # substring cleanup
        .str.strip()
        .replace({
            "GT (BT from 30.04)": "BT",
            "U": np.nan,
            "E": np.nan,
            "": np.nan,
        })
    )
    df_target["Species_2"] = (
        df_target["Species_2"]
        .str.strip()
        .replace({r"\?": "", r"\s*\(aggressiv\)": ""}, regex=True)  # substring cleanup
        .str.strip()
        .replace({
            "GT (BT from 30.04)": "BT",
            "U": np.nan,
            "E": np.nan,
            "": np.nan,
        })
    )

    # Clean up orientation column. The cardinal directions are redundant.
    df_target["Orientation"] = df_target["Orientation"].str.replace(r"[NESW]", "", regex=True)

    # Set coordinates. Currently, the same for all years.
    df_coordinates = pd.read_excel("nestbox_coordinates.xlsx", index_col=False)
    for nest in df_coordinates.itertuples():
        df_target.loc[df_target["ID"].astype(str) == nest.sensor_id, "Lat"] = nest.latitude
        df_target.loc[df_target["ID"].astype(str) == nest.sensor_id, "Lon"] = nest.longitude

    # Save the final data frame
    df_target.to_csv("nestbox_data_total.csv", index=False)

def format_number(value, digits=1):
    """Format a number for the tooltip. Missing values become an en dash."""
    if value is None:
        return "&ndash;"
    elif str(value) == "nan":
        return "?"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)

## Nest check data

#aggregate_nestbox_data(pl.Path("Data for students/Nestbox data"))

## Sensor Data
# Sensor stuff
#aggregate_ibutton_files(pl.Path(IBUTTON_PARENT_DIRECTORY))


# Map stuff
sensor_location = pd.read_excel("nestbox_coordinates.xlsx") # Todo update file with new data (and updates rotation for at least one sensor)

## Map Stuff
# Bounding box for relevant map section of TU Dortmund
min_lon, max_lon = 7.352, 7.47
min_lat, max_lat = 51.4755, 51.5045

# The actual map object
tu_map = folium.Map(
    tiles=None,
    max_bounds=True,
    location=[51.4921758, 7.4141904],
    zoom_start=16,
    min_lat=min_lat,
    max_lat=max_lat,
    min_lon=min_lon,
    max_lon=max_lon,
)
add_nest_css(tu_map)

# Tile sets for the map
for (i,tileset) in enumerate(["OpenStreetMap"]):
    folium.TileLayer(
        tiles=tileset,
        referrer_policy="strict-origin-when-cross-origin",
        show=(i == 0),
        name=tileset,
    ).add_to(tu_map)
folium.raster_layers.WmsTileLayer( # March
    url="https://www.wms.nrw.de/geobasis/wms_nw_dop",
    layers="nw_dop_rgb",
    fmt="image/png",
    transparent=False,
    name="Aerial Image, NRW",
    overlay=False,
    control=True,
    show=False,
    attr="© Geobasis NRW / Datenlizenz Deutschland Zero 2.0",
).add_to(tu_map)
folium.raster_layers.WmsTileLayer( # March
    url="https://www.wms.nrw.de/geobasis/wms_nw_dop",
    layers="nw_dop_cir",
    fmt="image/png",
    transparent=False,
    name="Aerial Image, NRW (DOP Infrared)",
    overlay=False,
    control=True,
    show=False,
    attr="© Geobasis NRW / Datenlizenz Deutschland Zero 2.0",
).add_to(tu_map)


# Add a little TU Dortmund logo
tu_logo = base64.b64encode(pl.Path("Logo_tud_logo_pantone_EN_kurz_VAR2_RGB.svg").read_bytes()).decode("ascii")
FloatImage(f"data:image/svg+xml;base64,{tu_logo}", bottom=1, left=0.5, width='250px').add_to(tu_map)

## For debugging. Enable when map bounding box should be visible.
#folium.CircleMarker([max_lat, min_lon], tooltip=f"Upper Left Corner {[max_lat, min_lon]}").add_to(tu_map)
#folium.CircleMarker([min_lat, min_lon], tooltip=f"Lower Left Corner {[min_lat, min_lon]}").add_to(tu_map)
#folium.CircleMarker([min_lat, max_lon], tooltip=f"Lower Right Corner {[min_lat, max_lon]}").add_to(tu_map)
#folium.CircleMarker([max_lat, max_lon], tooltip=f"Upper Right Corner {[max_lat, max_lon]}").add_to(tu_map)

# Draw sensors
years = []
nestbox_df = pd.read_csv("nestbox_data_total.csv")
sensor_types = sorted((nestbox_df["Year"].astype(str) + " " + nestbox_df["Type"]).unique())
tags_for_filters_labels = ["Great Tit", "Blue Tit", "Deaths", "Not Empty", "Has Chicks", "Has Eggs"]

iButton_data = pd.read_csv("iButton_measurements.csv", parse_dates=["Timestamp"])
iButton_data["Year"] = pd.to_datetime(iButton_data["Date"], format="%d/%m/%Y").dt.year
iButton_data["ID"] = iButton_data["ID"].astype(str)
iButton_data = iButton_data.set_index(["ID", "Year"]).sort_index()

# For coloring the temperature badges
temp_means = iButton_data[iButton_data["Variable"].isin(("TI", "TO")) & iButton_data["Timestamp"].dt.hour.between(DAY_START, DAY_END)].groupby(["ID", "Year", "Variable"])["Value"].mean()
temp_domain = tuple(temp_means.agg(["min", "max"]))


for year in [2024,2025,2026]:
    year_group = folium.FeatureGroup(name=str(year), show=(year == 2026))
    year_group.add_to(tu_map)
    years.append(year_group)

    nestbox_df_per_year = nestbox_df[nestbox_df["Year"] == year]
    for nestbox_metadata in nestbox_df_per_year.itertuples():
        if nestbox_metadata.Type == "iButton":
            nestbox = Nestbox(nestbox_metadata, iButton_data.loc[(nestbox_metadata.ID, nestbox_metadata.Year)])
        else:
            nestbox = Nestbox(nestbox_metadata)

        bird, bird_color = SPECIES.get(nestbox.Species_1, (None, None))

        tags_for_filter = [f"{nestbox.Year} {nestbox.Type}"]
        # Adds more tags for filters
        if "GT" in str(nestbox.Species_1) or "GT" in str(nestbox.Species_2):
            tags_for_filter.append("Great Tit")
        if "BT" in str(nestbox.Species_1) or "BT" in str(nestbox.Species_2):
            tags_for_filter.append("Blue Tit")
        if nestbox.Deaths:
            tags_for_filter.append("Deaths")
        if nestbox.Species_1 and str(nestbox.Species_1) != "nan":
            tags_for_filter.append("Not Empty")
        if nestbox.Chicks:
            tags_for_filter.append("Has Chicks")
        if nestbox.Eggs:
            tags_for_filter.append("Has Eggs")

        folium.Marker(
            location=[nestbox.Lat, nestbox.Lon],
            icon=nest_icon(
                bird=bird,
                bird_color=bird_color,
                sensor=nestbox.Type,
                t_in=None if nestbox.daytime_means is None else nestbox.daytime_means.get("TI"),
                t_out=None if nestbox.daytime_means is None else nestbox.daytime_means.get("TO"),
                temp_domain = temp_domain,
                eggs=nestbox.Eggs,
                chicks=nestbox.Chicks,
                dead=nestbox.Deaths,
                facing=nestbox.Orientation,
            ),
            lazy=True,
            tooltip=folium.Tooltip(nestbox.tooltip, sticky=False),
            popup=folium.Popup(nestbox.popup) if nestbox.popup else None,
            search_key=f"{nestbox.ID} ({nestbox.Type})",
            tags=tags_for_filter,
        ).add_to(year_group)

# Adds a layer control UI element
folium.LayerControl(collapsed=False).add_to(tu_map)
GroupedLayerControl(groups={"Year": years}, exclusive_groups=True).add_to(tu_map)

# Adds a toggle for marker badges
BadgeToggle().add_to(tu_map)

# Measurement tool
MeasureControl(
    primary_length_unit="meters",
    secondary_length_unit="kilometers",
    primary_area_unit="sqmeters",
).add_to(tu_map)

# Adds a full screen button
folium.plugins.Fullscreen(
    position="topright",
    title="Fullscreen",
    title_cancel="Exit fullscreen",
    force_separate_button=True,
).add_to(tu_map)

# Enables a display of lon/lat of the cursor's positon in the bottom right corner
# MousePosition().add_to(tu_map)

# Search bar for markers
Search(years[-1], search_label="searchKey", placeholder="Search for nestbox by ID or type").add_to(tu_map)

# Tag filter button
TagFilterButton(sensor_types).add_to(tu_map)
TagFilterButton(tags_for_filters_labels, icon="fa-tags").add_to(tu_map)

# Change the order of the zoom control buttons
css_controls = """
<style>
.leaflet-top.leaflet-left { display:flex; flex-direction:column; align-items:flex-start; }
.leaflet-top.leaflet-left .leaflet-control-zoom { order:99; }
</style>
"""
tu_map.get_root().header.add_child(folium.Element(css_controls))

# Favicon
icon = base64.b64encode(pl.Path("favicon_crow.svg").read_bytes()).decode("ascii")
tu_map.get_root().header.add_child(folium.Element(
    f'<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,{icon}">'
))

# Save map
tu_map.save('map.html')