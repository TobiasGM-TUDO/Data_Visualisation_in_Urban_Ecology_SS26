from branca.element import MacroElement
from folium.template import Template

# label -> CSS selector for the badge it controls
BADGES = {
    "Temperature": ".nest-temp",
    "Eggs":        ".nest-sw",
    "Chicks":      ".nest-s",
    "Deaths":      ".nest-se",
    "Orientation": ".nest-dir",
    "Markers": ".nest",
}


class BadgeToggle(MacroElement):
    """Checkbox control that shows/hides marker badges via CSS.

    ``visible`` sets which badges are on when the map loads: ``False`` for none,
    ``True`` for all, or a collection of labels for a mixed default.
    """

    _template = Template("""
        {% macro header(this,kwargs) %}
        <style>
        .badge-toggle { background:#fff; padding:6px 9px; border-radius:4px;
                        font:13px/1.5 system-ui,sans-serif; }
        .badge-toggle label { display:block; cursor:pointer; }
        .badge-toggle-title { font-weight:600; margin:0 0 4px; }
        {%- for key, sel in this.badges.items() %}
        .hide-{{ loop.index }} {{ sel }} { display:none; }
        {%- endfor %}
        </style>
        {% endmacro %}

        {% macro script(this,kwargs) %}
            var {{ this.get_name() }} = L.control({ position: '{{ this.position }}' });
            {{ this.get_name() }}.onAdd = function (map) {
                var visible = {{ this.visible|tojson }};
                var box = L.DomUtil.create('div', 'leaflet-bar badge-toggle');
                box.innerHTML =
                    '<div class="badge-toggle-title">' + {{ this.title|tojson }} + '</div>' +
                    {{ this.labels|tojson }}
                    .map(function (t, i) {
                        return '<label><input type="checkbox"' +
                               (visible[i] ? ' checked' : '') +
                               ' data-i="' + (i + 1) + '"> ' + t + '</label>';
                    }).join('');
                visible.forEach(function (on, i) {
                    if (!on) { L.DomUtil.addClass(map.getContainer(), 'hide-' + (i + 1)); }
                });
                L.DomEvent.disableClickPropagation(box);
                box.addEventListener('change', function (e) {
                    L.DomUtil[e.target.checked ? 'removeClass' : 'addClass'](
                        map.getContainer(), 'hide-' + e.target.dataset.i);
                });
                return box;
            };
            {{ this.get_name() }}.addTo({{ this._parent.get_name() }});
        {% endmacro %}
    """)

    def __init__(self, badges=BADGES, title="Marker Options", position="topright",
                 visible=False):
        super().__init__()
        self._name = "BadgeToggle"
        self.badges = badges
        self.title = title
        self.labels = list(badges)
        self.position = position
        self.visible = ([visible] * len(self.labels) if isinstance(visible, bool)
                        else [label in visible for label in self.labels])
