# generate_map.py

import os
from zipfile import ZipFile
from pykml import parser
from shapely.geometry import Point, box, mapping
import geopandas as gpd
import ee
import geemap.foliumap as geemap
import folium
from folium.raster_layers import ImageOverlay


# === Authenticate and Initialize Earth Engine ===
try:
    ee.Initialize(project='mynewproject-469023')
except Exception:
    ee.Authenticate()
    ee.Initialize(project='mynewproject-469023')


def extract_kmz_points_and_bounds(kmz_path: str, extract_dir: str = "extracted"):
    """Extract points and bounding box from KMZ."""
    os.makedirs(extract_dir, exist_ok=True)

    with ZipFile(kmz_path, 'r') as kmz:
        kmz.extractall(extract_dir)

    kml_file = next(
        (os.path.join(extract_dir, f) for f in os.listdir(extract_dir) if f.endswith('.kml')),
        None
    )
    if not kml_file:
        raise FileNotFoundError("No .kml file found in the KMZ.")

    with open(kml_file, 'r', encoding='utf-8') as f:
        root = parser.parse(f).getroot()

    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    placemarks = root.xpath('.//kml:Placemark[kml:Point]', namespaces=ns)
    if not placemarks:
        raise ValueError("No Point placemarks found in the KML.")

    points = []
    for i, pm in enumerate(placemarks):
        coords = pm.Point.coordinates.text.strip()
        lon, lat, *_ = map(float, coords.split(','))
        points.append(Point(lon, lat))
        print(f" Point {i+1}: Longitude = {lon:.6f}, Latitude = {lat:.6f}")

    gdf = gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")
    minx, miny, maxx, maxy = gdf.total_bounds
    image_bounds = [[miny, minx], [maxy, maxx]]
    bbox = box(minx, miny, maxx, maxy)

    # Save bbox as GeoJSON
    gpd.GeoDataFrame(geometry=[bbox], crs="EPSG:4326").to_file(
        os.path.join(extract_dir, "kmz_bbox.geojson"), driver="GeoJSON"
    )

    return points, image_bounds, bbox


def display_interactive_map(image_path, image_bounds, points, bbox, output_html="interactive_map.html"):
    """Render interactive map with image overlay, markers, and bounding box."""
    center = [points[0].y, points[0].x]
    m = geemap.Map(center=center, zoom=16, basemap='SATELLITE')

    # Add image overlay
    image_overlay = ImageOverlay(
        name='Contour Overlay',
        image=image_path,
        bounds=image_bounds,
        opacity=0.8,
        interactive=True,
        cross_origin=False,
        zindex=1
    )
    image_overlay.options['smooth'] = False
    image_overlay.add_to(m)

    # Add points as blue dots
    for pt in points:
        folium.CircleMarker(
            location=[pt.y, pt.x],
            radius=2,
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.8,
            popup='KMZ Point'
        ).add_to(m)

    # Add bounding box
    bbox_geojson = {
        "type": "Feature",
        "geometry": mapping(bbox),
        "properties": {}
    }
    folium.GeoJson(
        bbox_geojson,
        name='KMZ Bounding Box',
        style_function=lambda x: {
            "color": "blue",
            "weight": 0.5,
            "dashArray": "5, 5",
            "fillOpacity": 0.0
        }
    ).add_to(m)

    # Save map
    m.save(output_html)
    print(f"Interactive map saved to: {output_html}")

    inject_bounds_script(output_html)


def inject_bounds_script(html_file):
    """Inject robust controls: mutation-observer + composed transforms so rotation sticks."""
    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()

    js_code = r"""
<div style="position:absolute; top:10px; right:10px; z-index:9999; background:rgba(255,255,255,0.95); padding:10px; border-radius:6px; font-family:Arial,Helvetica,sans-serif;">
  <div style="margin-bottom:8px;">
    <label>Move Scale: </label>
    <input type="number" id="moveScale" value="0.1" step="0.01" min="0.01" style="width:60px;">
    <br>
    <button onclick="moveImage('up')" style="margin:2px;">⬆️</button>
    <button onclick="moveImage('down')" style="margin:2px;">⬇️</button>
    <button onclick="moveImage('left')" style="margin:2px;">⬅️</button>
    <button onclick="moveImage('right')" style="margin:2px;">➡️</button>
  </div>

  <div style="margin-bottom:8px;">
    <label>Scale Factor: </label>
    <input type="number" id="scaleAmount" value="1.1" step="0.1" min="0.1" style="width:60px;">
    <br>
    <button onclick="scaleImage('expand')" style="margin:2px;">🔍 Expand</button>
    <button onclick="scaleImage('contract')" style="margin:2px;">🔎 Contract</button>
  </div>

  <div style="margin-bottom:8px;">
    <label>Rotation (deg): </label>
    <input type="number" id="rotationDegrees" value="15" step="1" style="width:60px;">
    <br>
    <button onclick="rotateImage('left')" style="margin:2px;">↺</button>
    <button onclick="rotateImage('right')" style="margin:2px;">↻</button>
  </div>

  <div>
    <button onclick="resetImageBounds()" style="background:#ff6b6b; color:white;">🔁 Reset</button>
  </div>
</div>

<script>
(() => {
  let map = null;
  let overlay = null;
  let originalBounds = null;
  let currentRotation = 0;

  // --- Helper: find the Leaflet Map instance on the page ---
  function findMap() {
    if (map && map instanceof L.Map) return map;
    for (const k in window) {
      try {
        const v = window[k];
        if (v && v instanceof L.Map) { map = v; break; }
      } catch(e) { /* ignore cross-origin / exotic props */ }
    }
    return map;
  }

  // --- Helper: find the first ImageOverlay (or choose filter here) ---
  function findOverlay() {
    if (overlay && overlay instanceof L.ImageOverlay) return overlay;
    const m = findMap();
    if (!m) return null;
    let found = null;
    m.eachLayer(layer => {
      if (!found && layer instanceof L.ImageOverlay) found = layer;
    });
    if (found) overlay = found;
    return overlay;
  }

  // --- Apply rotation to a given img element by composing with Leaflet's transform ---
  function applyRotationTo(img) {
  if (!img) return;
  try {
    if (img.__setting) return;
    img.__setting = true;

    // Always set rotation origin to center
    img.style.transformOrigin = "center center";

    // strip existing rotate() from transform
    let inline = (img.style && img.style.transform) ? img.style.transform : '';
    inline = inline.replace(/rotate\([^)]*\)/g, '').trim();

    if (!inline) {
      const cs = window.getComputedStyle(img);
      if (cs) inline = (cs.transform && cs.transform !== 'none') ? cs.transform : '';
    }

    const rotationStr = ` rotate(${currentRotation}deg)`;
    img.style.transform = (inline ? inline + rotationStr : rotationStr);

    img.dataset.__desiredRotation = String(currentRotation);

    requestAnimationFrame(() => { img.__setting = false; });
  } catch (e) {
    console.warn("applyRotationTo error:", e);
    if (img) img.__setting = false;
  }
}


  // --- Attach observers to handle style changes and element replacement ---
  function attachImageObservers(img) {
    if (!img) return;

    // don't attach twice
    if (img.__obsAttached) {
      // reapply once when attaching again
      applyRotationTo(img);
      return;
    }
    img.__obsAttached = true;

    // Observe inline style changes (Leaflet tends to set inline style)
    const attrObs = new MutationObserver(mutations => {
      for (const m of mutations) {
        if (m.type === 'attributes' && m.attributeName === 'style') {
          // If we recently set the style, skip (guard __setting)
          if (img.__setting) continue;
          // recompose rotation on the newly set transform
          applyRotationTo(img);
        }
        if (m.type === 'attributes' && m.attributeName === 'src') {
          // new source — reapply
          applyRotationTo(img);
        }
      }
    });
    attrObs.observe(img, { attributes: true, attributeFilter: ['style', 'src'] });
    img.__attrObserver = attrObs;

    // Observe parent for child replacements (Leaflet sometimes replaces the <img>)
    const parent = img.parentNode;
    if (parent && !parent.__childObserver) {
      const childObs = new MutationObserver(changes => {
        for (const c of changes) {
          if (c.type === 'childList') {
            for (const node of c.addedNodes) {
              if (node && node.tagName && node.tagName.toLowerCase() === 'img') {
                // attach to new image and apply rotation
                attachImageObservers(node);
                applyRotationTo(node);
              }
            }
          }
        }
      });
      childObs.observe(parent, { childList: true });
      parent.__childObserver = childObs;
    }

    // initial apply
    applyRotationTo(img);
  }

  // --- Reapply to current overlay image (safe wrapper) ---
  function reapplyToOverlayImage() {
    const ov = findOverlay();
    if (!ov) return;
    const img = (typeof ov.getElement === 'function') ? ov.getElement() : ov._image || null;
    if (img) attachImageObservers(img);
  }

  // --- Controls (move / scale / rotate / reset) ---
  window.moveImage = function(direction) {
    const ov = findOverlay(); if (!ov) return;
    const moveScale = parseFloat(document.getElementById('moveScale').value) || 0.1;
    const b = ov.getBounds();
    const sw = b.getSouthWest(), ne = b.getNorthEast();
    const latSpan = ne.lat - sw.lat, lngSpan = ne.lng - sw.lng;
    let dLat = 0, dLng = 0;
    if (direction === 'up') dLat =  latSpan * moveScale;
    if (direction === 'down') dLat = -latSpan * moveScale;
    if (direction === 'left') dLng = -lngSpan * moveScale;
    if (direction === 'right') dLng =  lngSpan * moveScale;
    const newB = L.latLngBounds([sw.lat + dLat, sw.lng + dLng],[ne.lat + dLat, ne.lng + dLng]);
    ov.setBounds(newB);
    // reapply after leaflet updates
    requestAnimationFrame(reapplyToOverlayImage);
  };

  window.scaleImage = function(action) {
    const ov = findOverlay(); if (!ov) return;
    const scaleAmount = parseFloat(document.getElementById('scaleAmount').value) || 1.1;
    const b = ov.getBounds();
    const sw = b.getSouthWest(), ne = b.getNorthEast();
    const cLat = (sw.lat + ne.lat) / 2, cLng = (sw.lng + ne.lng) / 2;
    const factor = (action === 'expand') ? scaleAmount : (1 / scaleAmount);
    const halfLat = (ne.lat - sw.lat) * factor / 2;
    const halfLng = (ne.lng - sw.lng) * factor / 2;
    const newB = L.latLngBounds([cLat - halfLat, cLng - halfLng],[cLat + halfLat, cLng + halfLng]);
    ov.setBounds(newB);
    requestAnimationFrame(reapplyToOverlayImage);
  };

  window.rotateImage = function(direction) {
    const step = parseFloat(document.getElementById('rotationDegrees').value) || 15;
    currentRotation = (currentRotation + (direction === 'left' ? -step : step)) % 360;
    reapplyToOverlayImage();
  };

  window.resetImageBounds = function() {
    const ov = findOverlay(); if (!ov || !originalBounds) return;
    ov.setBounds(originalBounds);
    currentRotation = 0;
    requestAnimationFrame(reapplyToOverlayImage);
  };

  // --- Initialization: find overlay + hooks to reapply on map/overlay events ---
  function init() {
    const m = findMap();
    const ov = findOverlay();
    if (!m || !ov) return setTimeout(init, 200);

    originalBounds = ov.getBounds();

    // attach to current overlay image
    reapplyToOverlayImage();

    // reapply rotation when overlay or map changes
    try {
      if (ov.on) {
        ov.on('load', () => setTimeout(reapplyToOverlayImage, 0));
        ov.on('update', () => setTimeout(reapplyToOverlayImage, 0));
      }
      m.on('zoomend', () => setTimeout(reapplyToOverlayImage, 0));
      m.on('moveend', () => setTimeout(reapplyToOverlayImage, 0));
    } catch (e) { console.warn("event hook error", e); }
  }

  // start
  init();
})();
</script>
"""

    if "</body>" in html:
        html = html.replace("</body>", js_code + "\n</body>")

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
def select_file_gui():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select KMZ File",
        filetypes=[("KMZ Files", "*.kmz *.xls")]
    )
    if not file_path:
        messagebox.showwarning("No file selected", "Please select an Excel file to proceed.")
        sys.exit(0)
    return file_path

if __name__ == "__main__":
    kmz_path = select_file_gui()
    image_path = "output_files/groundwater_contour_true_scale.png"

    points, image_bounds, bbox = extract_kmz_points_and_bounds(kmz_path)
    display_interactive_map(image_path, image_bounds, points, bbox)
