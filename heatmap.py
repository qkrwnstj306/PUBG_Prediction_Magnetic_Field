import requests
import json
import numpy as np
import matplotlib.pyplot as plt
import cv2
import random
import os

Sanhok_map_image_path = "sanhok_img.png"

# 🔹 PUBG API 설정
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiI5ZGE1MzUyMC1kZGMzLTAxM2QtYWVlYi0wNjFhOWQ1YjYxYWYiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzQxMzgwNTgxLCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6InFrcnduc3RqIn0.fELc21Gr8jFivjpIzkavvzef-lMVjH-2L4ARym55bQE"
PLATFORM = "kakao"
PLAYER_NAME = "Jangmonky" ## Jangmonky

# 🔹 PUBG API 요청 헤더
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json"
}

# 🔹 API 요청 함수 (예외 처리 추가)
def fetch_json(url, headers):
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(f"API 요청 실패: {url}, 상태 코드: {response.status_code}")
    return response.json()

# 🔹 특정 플레이어의 매치 목록 가져오기
player_url = f"https://api.pubg.com/shards/{PLATFORM}/players?filter[playerNames]={PLAYER_NAME}"
player_data = fetch_json(player_url, HEADERS)

# 🔹 플레이어의 최근 매치 중 'Sanhok'에서 진행된 매치만 필터링
sanhok_matches = []
for match in player_data["data"][0]["relationships"]["matches"]["data"]:
    match_id = match["id"]

    match_url = f"https://api.pubg.com/shards/{PLATFORM}/matches/{match_id}"
    match_data = fetch_json(match_url, HEADERS)

    # 맵 정보 확인 및 게임 모드 필터링
    map_name = match_data["data"]["attributes"]["mapName"]
    game_mode = match_data["data"]["attributes"]["gameMode"]  # 게임 모드 정보

    if map_name == "Savage_Main" and (game_mode == "squad" or game_mode == "solo"):
        sanhok_matches.append(match_id)

if not sanhok_matches:
    raise ValueError("Sanhok에서 진행된 스쿼드 또는 일반 게임 매치를 찾을 수 없습니다.")

MATCH_ID = random.choice(sanhok_matches)
print(f"🎯 선택된 매치 ID: {MATCH_ID}")

###
MATCH_ID = 'ab4472da-eb4e-4328-820c-105675a1a332'

# 🔹 텔레메트리 데이터 URL 가져오기
match_url = f"https://api.pubg.com/shards/{PLATFORM}/matches/{MATCH_ID}"
match_data = fetch_json(match_url, HEADERS)

# participants = [item for item in match_data["included"] if item["type"] == "participant"]
# print(participants)

telemetry_url = None
for item in match_data["included"]:
    if item["type"] == "asset" and item["attributes"].get("name") == "telemetry":
        telemetry_url = item["attributes"]["URL"]
        break

if telemetry_url is None:
    raise ValueError("텔레메트리 URL을 찾을 수 없습니다.")

# 🔹 텔레메트리 데이터 요청
telemetry_data = fetch_json(telemetry_url, HEADERS)

# 🔹 Sanhok 맵 크기 설정 (4km x 4km)
MAP_SIZE = 400000

# 🔹 각 페이즈별 자기장 정보 저장
circle_data = {}
previous_radius = None
current_phase = 0  # 초기 페이즈 설정
radius_count = 0  # 같은 반지름이 유지된 횟수
previous_phase = False

for event in telemetry_data:
    if event["_T"] == "LogGameStatePeriodic":
        game_state = event.get("gameState", {})

        # 자기장 반지름 가져오기
        radius = game_state.get("safetyZoneRadius")

        # 이전 반지름과 비교하여 페이즈 변경 감지
        if previous_radius is not None and radius == previous_radius:
            radius_count += 1  # 동일한 반지름이 두 번 이상 유지되면 페이즈 변경
        else:
            previous_phase = True
            radius_count = 0  # 반지름이 변경되면 페이즈가 움직이고 있음. 카운트 초기화

        # 동일한 반지름이 2번 이상 유지되면 새로운 페이즈로 설정
        if radius_count >= 1:
            if previous_phase == True:
                current_phase += 1  # 새로운 페이즈
                previous_phase = False

        previous_radius = radius  # 현재 반지름 업데이트

        center_x = game_state["safetyZonePosition"]["x"]
        center_y = game_state["safetyZonePosition"]["y"]
        # ✅ 해당 페이즈에 아직 저장된 값이 없다면 저장 (한 번만 저장)
        if current_phase not in circle_data:
            circle_data[current_phase] = (center_x, center_y, radius)
        # 이미 해당 페이즈에 자기장이 저장되었다면, 이후에는 저장하지 않음
        # 그 외 조건은 필요없음

if not circle_data:
    raise ValueError("자기장 데이터가 없습니다. 텔레메트리 데이터를 확인하세요.")

def generate_overlayed_heatmap(phase, circle, map_image_path, save_path="heatmaps/"):
    os.makedirs(save_path, exist_ok=True)  # 저장 폴더 생성

    # Sanhok 맵 이미지 로드 (1008x1008 해상도)
    map_image = cv2.imread(map_image_path)
    map_image = cv2.resize(map_image, (1008, 1008))
    
    # PUBG 좌표계를 이미지 좌표계로 변환 (y 좌표 뒤집기)
    x_img = int((circle[0] / MAP_SIZE) * 1008)
    y_img = int((circle[1] / MAP_SIZE) * 1008)  # y 좌표 반전
    r_img = int((circle[2] / MAP_SIZE) * 1008)
    
    # 히트맵 생성 (원형 자기장)
    heatmap = np.zeros((1008, 1008), dtype=np.float32)
    cv2.circle(heatmap, (x_img, y_img), r_img, 1, -1)
    
    # 히트맵에 컬러맵 적용
    heatmap_colored = cv2.applyColorMap(np.uint8(255 * heatmap), cv2.COLORMAP_HOT)
    
    # 맵 이미지와 히트맵 합성 (알파값 조절)
    overlayed_image = cv2.addWeighted(map_image, 0.7, heatmap_colored, 0.3, 0)
    
    # 시각화: 여백 제거 설정 추가
    plt.figure(figsize=(6, 6))
    plt.imshow(cv2.cvtColor(overlayed_image, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)  # 여백 제거
    plt.title(f"Phase {phase} Circle Overlay (Sanhok)")
    plt.savefig(f"{save_path}sanhok_phase_{phase}_overlay.png", bbox_inches="tight", pad_inches=0, dpi=300)
    plt.close()

# 🔹 모든 페이즈에 대해 오버레이된 히트맵 생성
skip_0 = True
for phase, circle in circle_data.items():
    if skip_0 == True:
        skip_0 = False
        continue
    generate_overlayed_heatmap(phase, circle, Sanhok_map_image_path)

print("✅ Sanhok 페이즈별 자기장 히트맵이 저장되었습니다!")
