import obsws_python as obs

# 🔹 OBS WebSocket 연결 설정
OBS_HOST = "localhost"
OBS_PORT = 4455

# 🔹 OBS WebSocket 클라이언트 연결
client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT)

# 🔹 씬 목록 가져오기
scene_data = client.get_scene_list().__dict__  # ✅ 딕셔너리 변환
scenes = scene_data["scenes"]  # ✅ 씬 리스트 가져오기

print("🔹 현재 OBS 씬 목록:")
for scene in scenes:
    print(f" - {scene['sceneName']}")  # ✅ OBS WebSocket 최신 버전에서 'sceneName'을 사용
