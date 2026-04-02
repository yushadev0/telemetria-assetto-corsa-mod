import ac
import acsys

timer_lb = 0.0
timer_map = 0.0
lbl_status = None
FILE_PATH_LB = "apps/python/TelemetriaLB/lb.json"
FILE_PATH_MAP = "apps/python/TelemetriaLB/map.json"

def acMain(ac_version):
    global lbl_status
    appWindow = ac.newApp("Telemetria LB")
    ac.setSize(appWindow, 300, 100)
    lbl_status = ac.addLabel(appWindow, "IPC: ACTIVE (NO AI)")
    ac.setPosition(lbl_status, 10, 30)
    ac.setFontColor(lbl_status, 0.1, 1.0, 0.1, 1.0)
    return "Telemetria LB"

def acUpdate(deltaT):
    global timer_lb, timer_map, lbl_status
    timer_lb += deltaT
    timer_map += deltaT
    
    try:
        cars_count = ac.getCarsCount()
        
        # --- HAFİF RADAR MOTORU (10 FPS) ---
        if timer_map > 0.1:
            timer_map = 0.0
            map_str = '{"map":['
            for i in range(cars_count):
                if i > 0: map_str += ','
                pos3d = ac.getCarState(i, acsys.CS.WorldPosition)
                # Sadece ID, X ve Z değerleri fırlatılır!
                map_str += '[' + str(i) + ',' + str(round(pos3d[0], 2)) + ',' + str(round(pos3d[2], 2)) + ']'
            map_str += ']}'
            
            with open(FILE_PATH_MAP, "w") as f:
                f.write(map_str)

        # --- LİDERLİK TABLOSU MOTORU (2 FPS) ---
        if timer_lb > 0.5:
            timer_lb = 0.0
            lb_list = []
            track_length = ac.getTrackLength(0)
            if track_length <= 0: track_length = 5000.0
                
            session_fastest_ms = 999999999 
            virtual_yellow_flag = "false"
            
            for i in range(cars_count):
                name = ac.getDriverName(i)
                if name != "":
                    pos = ac.getCarRealTimeLeaderboardPosition(i) + 1
                    best_lap = ac.getCarState(i, acsys.CS.BestLap)
                    cur_lap = ac.getCarState(i, acsys.CS.LapTime)
                    is_pit = bool(ac.isCarInPitline(i)) or bool(ac.isCarInPit(i))
                    spline = ac.getCarState(i, acsys.CS.NormalizedSplinePosition)
                    lap_count = ac.getCarState(i, acsys.CS.LapCount)
                    speed_kmh = ac.getCarState(i, acsys.CS.SpeedKMH)
                    speed_ms = max(speed_kmh / 3.6, 5.0) 
                    total_dist = (lap_count + spline) * track_length
                    
                    if best_lap > 0 and best_lap < session_fastest_ms:
                        session_fastest_ms = best_lap
                    
                    if not is_pit and speed_kmh < 20 and 0.05 < spline < 0.95:
                        virtual_yellow_flag = "true" 
                    
                    clean_name = name.replace('"', '').replace('\\', '')
                    lb_list.append({
                        "id": i, "pos": pos, "name": clean_name, "best_lap": best_lap,
                        "cur_lap": cur_lap, "is_pit": is_pit, "total_dist": total_dist, "speed_ms": speed_ms
                    })
            
            lb_list.sort(key=lambda x: x["pos"])
            
            for idx, car in enumerate(lb_list):
                display_time = car["best_lap"] if car["best_lap"] > 0 else car["cur_lap"]
                if car["is_pit"] and display_time == 0:
                    car["time_str"] = "0:00.000"
                else:
                    m = int((display_time / 1000) // 60)
                    s = int((display_time / 1000) % 60)
                    ms = int(display_time % 1000)
                    car["time_str"] = "{}:{:02d}.{:03d}".format(m, s, ms)
                    
                if car["is_pit"]: car["delta_str"] = "PIT"
                elif car["pos"] == 1: car["delta_str"] = "LEADER"
                else:
                    if idx > 0:
                        time_gap = abs(lb_list[idx-1]["total_dist"] - car["total_dist"]) / car["speed_ms"]
                        car["delta_str"] = "+{:.3f}".format(time_gap)
                    else: car["delta_str"] = "---"

            player_pos = 1
            for car in lb_list:
                if car["id"] == 0:
                    player_pos = car["pos"]
                    break
            
            if session_fastest_ms == 999999999: session_fastest_ms = 0
                
            json_str = '{"session_fastest":' + str(session_fastest_ms) + ',"yellow_flag":' + virtual_yellow_flag + ',"player_pos":' + str(player_pos) + ',"leaderboard": ['
            added_count = 0
            
            for car in lb_list:
                p = car["pos"]
                if p <= 3 or p == player_pos - 1 or p == player_pos or p == player_pos + 1:
                    if added_count > 0: json_str += ','
                    is_player = "true" if car["id"] == 0 else "false"
                    is_fastest = "true" if (car["best_lap"] > 0 and car["best_lap"] == session_fastest_ms) else "false"
                    json_str += '{"id":' + str(car["id"]) + ',"pos":' + str(car["pos"]) + ',"name":"' + car["name"] + '","delta":"' + car["delta_str"] + '","time":"' + car["time_str"] + '","is_player":' + is_player + ',"is_fastest":' + is_fastest + '}'
                    added_count += 1
                    if added_count >= 6: break
                        
            json_str += ']}'
            
            with open(FILE_PATH_LB, "w", encoding="utf-8") as f:
                f.write(json_str)
                
            ac.setText(lbl_status, "IPC: RUNNING (" + str(cars_count) + " CARS)")
            
    except Exception as e:
        ac.setText(lbl_status, "ERR: " + str(e))