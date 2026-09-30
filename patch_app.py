import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. We need to add the advance_missions logic to the sidebar simulate button.
sidebar_target = """        if st.button("▶ Step Simulation", use_container_width=True):
            event = st.session_state.simulator.next_event()
            if event:
                apply_simulation_event(st.session_state.crisis_state, event)"""

sidebar_replace = """        if st.button("▶ Step Simulation", use_container_width=True):
            st.session_state.crisis_state.advance_missions(step_percent=15.0)
            event = st.session_state.simulator.next_event()
            if event:
                apply_simulation_event(st.session_state.crisis_state, event)
            st.rerun()"""

content = content.replace(sidebar_target, sidebar_replace)

# 2. Modify map to show active missions and dispatch preview
map_start = content.find("# ── CENTER: Map")
map_end = content.find("# ── RIGHT: Command Decision Panel")
if map_start != -1 and map_end != -1:
    new_map = """# ── CENTER: Map ───────────────────────────────────────────────────────────

with col_center:
    st.markdown("#### 🗺 Situation Map")
    st.caption("SIMULATION DATA — Map tiles: OpenStreetMap")

    try:
        import folium
        from streamlit_folium import st_folium

        m = folium.Map(
            location=[21.175, 72.830], zoom_start=13,
            tiles="OpenStreetMap",
        )

        # Incidents
        for inc in state.incidents:
            sev = inc.severity or 0
            color = "red" if sev >= 9 else "orange" if sev >= 7 else "beige" if sev >= 4 else "green"
            urg = inc.urgency.value if inc.urgency else "?"
            folium.CircleMarker(
                [inc.latitude, inc.longitude],
                radius=9 + sev,
                color=color, fill=True, fill_opacity=0.75, weight=2,
                popup=folium.Popup(
                    f"<b>{inc.id}</b><br>{inc.type}<br>Severity {sev} | {urg}<br>"
                    f"Affected: {inc.people_affected} | Trapped: {inc.people_trapped}",
                    max_width=200,
                ),
                tooltip=f"{inc.id}: {inc.type} [{urg}]",
            ).add_to(m)
            folium.map.Marker(
                [inc.latitude, inc.longitude],
                icon=folium.DivIcon(
                    html=f'<div style="font-size:9px;color:white;font-weight:bold;'
                         f'white-space:nowrap;text-shadow:1px 1px 2px black;">{inc.id}</div>',
                    icon_size=(60, 14), icon_anchor=(0, -5),
                ),
            ).add_to(m)

        # Units
        for unit in state.units:
            if unit.status == UnitStatus.BROKEN_DOWN:
                ucolor = "red"
            elif unit.status == UnitStatus.AVAILABLE:
                ucolor = "green"
            elif unit.status == UnitStatus.EN_ROUTE:
                ucolor = "blue"
            elif unit.status == UnitStatus.ON_SCENE:
                ucolor = "purple"
            else:
                ucolor = "gray"
                
            uicon = "plus-sign" if unit.type == UnitType.AMBULANCE else "home"
            # If unit is en_route, use its mission coordinates
            lat, lon = unit.latitude, unit.longitude
            for m_id, mission in state.active_missions.items():
                if mission.unit_id == unit.id and mission.status == "EN_ROUTE":
                    lat, lon = mission.current_latitude, mission.current_longitude
            
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(
                    f"<b>{unit.id}</b><br>Type: {unit.type.value}<br>Status: {unit.status.value}",
                    max_width=160,
                ),
                tooltip=f"{unit.id} [{unit.status.value}]",
                icon=folium.Icon(color=ucolor, icon=uicon, prefix="glyphicon"),
            ).add_to(m)

        # Active missions and preview routes
        preview_route = st.session_state.get('preview_route')
        if preview_route and preview_route.waypoints:
            folium.PolyLine(
                preview_route.waypoints,
                color="#eab308", weight=4, opacity=0.8, dash_array="5",
                tooltip=f"PREVIEW: {preview_route.name} | ETA {preview_route.eta_minutes:.1f} min",
            ).add_to(m)
            
        for m_id, mission in state.active_missions.items():
            if mission.status == "EN_ROUTE":
                r = state.get_mission_route(m_id)
                if r and r.waypoints:
                    folium.PolyLine(
                        r.waypoints,
                        color="#3b82f6", weight=3, opacity=0.8,
                        tooltip=f"ACTIVE: {mission.unit_id} → {mission.incident_id} | ETA {mission.eta_minutes} min",
                    ).add_to(m)

        # Blocked roads
        for road in state.road_conditions:
            if road.blocked:
                folium.PolyLine(
                    [[road.from_lat, road.from_lon], [road.to_lat, road.to_lon]],
                    color="#ef4444", weight=5, dash_array="8",
                    tooltip=f"BLOCKED: {road.name}",
                ).add_to(m)

        # Legend
        legend_html = \"\"\"
        <div style="position:fixed;bottom:20px;left:20px;z-index:9999;
            background:#111827;border:1px solid #1e293b;border-radius:6px;padding:8px 12px;
            font-family:Inter,sans-serif;font-size:11px;color:#94a3b8;">
          <div style="font-weight:700;color:#e2e8f0;margin-bottom:4px;">Legend</div>
          <div><span style="color:#ef4444;">●</span> CRITICAL Incident</div>
          <div><span style="color:#22c55e;">▲</span> Unit (Available)</div>
          <div><span style="color:#3b82f6;">▲</span> Unit (En-Route)</div>
          <div><span style="color:#3b82f6;">━</span> Active Route</div>
          <div><span style="color:#eab308;">╌</span> Preview Route</div>
          <div><span style="color:#ef4444;">╌</span> Blocked Road</div>
        </div>\"\"\"
        m.get_root().html.add_child(folium.Element(legend_html))

        st_folium(m, width=None, height=420, returned_objects=[])

    except ImportError:
        st.warning("Install folium and streamlit-folium for map view: `pip install folium streamlit-folium`")

"""
    content = content[:map_start] + new_map + content[map_end:]

# 3. Replace RIGHT column with Dispatch UI
right_col_start = content.find("# ── RIGHT: Command Decision Panel")
bottom_tabs_start = content.find("# ---------------------------------------------------------------------------\\n# BOTTOM TABS")
if right_col_start != -1 and bottom_tabs_start != -1:
    new_right = """# ── RIGHT: Command Decision Panel ────────────────────────────────────────

with col_right:
    st.markdown("#### 🎯 Dispatch Command")
    
    # 1. Select Incident
    inc_opts = [""] + [i.id for i in state.incidents]
    sel_inc = st.selectbox("Select Incident", inc_opts)
    
    # 2. Select Unit
    avail_units = [u.id for u in state.units if u.status in (UnitStatus.AVAILABLE, UnitStatus.ASSIGNED)]
    sel_unit = st.selectbox("Select Unit", [""] + avail_units)
    
    # Calculate routes if both selected
    from backend.route import calculate_routes
    if sel_inc and sel_unit:
        inc = state.get_incident(sel_inc)
        unit = state.get_unit(sel_unit)
        if inc and unit:
            routes = calculate_routes(
                unit.latitude, unit.longitude,
                inc.latitude, inc.longitude,
                state.road_conditions
            )
            
            if not routes:
                st.error("No routes calculated.")
                st.session_state.preview_route = None
            else:
                st.markdown("##### Route Options")
                route_choices = {}
                for r in routes:
                    lbl = f"{r.name} ({r.eta_minutes:.1f} min | {r.distance_km:.1f} km) - {r.status}"
                    route_choices[lbl] = r
                
                sel_r_lbl = st.radio("Select Route", list(route_choices.keys()))
                sel_route = route_choices.get(sel_r_lbl)
                st.session_state.preview_route = sel_route
                
                if sel_route and sel_route.status == "FEASIBLE":
                    if st.button("🚀 DISPATCH UNIT", type="primary", use_container_width=True):
                        state.dispatch_unit(unit.id, inc.id, sel_route)
                        st.session_state.preview_route = None
                        st.rerun()
                elif sel_route:
                    st.error(f"Cannot dispatch: {sel_route.status} - {sel_route.reason}")
    else:
        st.session_state.preview_route = None
        
    st.markdown("---")
    st.markdown("##### 📡 Active Missions")
    active_count = 0
    for m_id, mission in state.active_missions.items():
        if mission.status == "EN_ROUTE":
            active_count += 1
            st.markdown(f\"\"\"
<div style="background:#0f1923;border:1px solid #1e3a5f;border-radius:6px;padding:10px;margin-bottom:8px;">
  <div style="font-size:0.7rem;color:#60a5fa;font-weight:700;">{mission.unit_id} → {mission.incident_id}</div>
  <div style="font-size:0.65rem;color:#94a3b8;margin-top:2px;">Route: {mission.route_id}</div>
  <div style="font-size:0.65rem;color:#94a3b8;">ETA: {mission.eta_minutes:.1f} min | Dist: {mission.distance_remaining_km:.1f} km</div>
  <div style="width:100%;background:#1e293b;height:4px;border-radius:2px;margin-top:6px;">
    <div style="width:{mission.progress_percent}%;background:#3b82f6;height:100%;border-radius:2px;"></div>
  </div>
</div>\"\"\", unsafe_allow_html=True)
        elif mission.status == "INTERRUPTED":
            active_count += 1
            st.markdown(f\"\"\"
<div style="background:#450a0a;border:1px solid #ef4444;border-radius:6px;padding:10px;margin-bottom:8px;">
  <div style="font-size:0.7rem;color:#fca5a5;font-weight:700;">⚠ {mission.unit_id} ROUTE INTERRUPTED</div>
  <div style="font-size:0.65rem;color:#cbd5e1;margin-top:2px;">Target: {mission.incident_id}</div>
  <div style="font-size:0.65rem;color:#cbd5e1;">Awaiting Commander intervention.</div>
</div>\"\"\", unsafe_allow_html=True)

    if active_count == 0:
        st.caption("No active missions.")
        
"""
    content = content[:right_col_start] + new_right + content[bottom_tabs_start:]

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("app.py updated successfully.")
