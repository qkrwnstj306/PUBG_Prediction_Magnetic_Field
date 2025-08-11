import requests
import json
import numpy as np
import matplotlib.pyplot as plt
import cv2
import random
import os

# Sanhok 맵 이미지 (1008x1008 해상도)
Sanhok_map_image_path = "sanhok_img.png"

# 🔹 PUBG API 설정
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiI5ZGE1MzUyMC1kZGMzLTAxM2QtYWVlYi0wNjFhOWQ1YjYxYWYiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzQxMzgwNTgxLCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6InFrcnduc3RqIn0.fELc21Gr8jFivjpIzkavvzef-lMVjH-2L4ARym55bQE"
PLATFORM = "kakao"
# 여러 플레이어 (혹은 여러 유저)를 리스트로 지정
player_names = ["naverdaumgoogle1", "KKP_GREECE", "Socute-__-", "beenbp-", "shotzlzone-_-", "DDUXOL", "Chill9uy_-", "InvBaNaNa", "100RiHyang", "dbalsld"
                , "KKP_TaeSik", "Uality_A", "Team_Util_D", "aaaac_e", "als_ha", "SSIN-_o", "N3_Bongsoon", "akakt123", "jisu0203", "larszooom", "SIKSE77I",
                "JUNYK7", "Kitemaster", "Bigho-ng", "CLoud_Kc", "chuchu_93", "M_ZZZZ9", "Aaa-men", "ASAP-_", "10839516", "dogdrake12", "Matt_D78", "HHHBUM"]  

# 🔹 API 요청 헤더
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json"
}

# 🔹 API 요청 함수 (예외 처리 포함)
def fetch_json(url, headers):
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise ValueError(f"API 요청 실패: {url}, 상태 코드: {response.status_code}")
    return response.json()

# Sanhok 맵의 실제 크기 (단위: 미터; Sanhok은 400,000 x 400,000 좌표)
MAP_SIZE = 400000
# 최종 이미지 해상도 (Sanhok 맵 이미지 크기)
IMG_SIZE = 1008

# 각 페이즈별 누적 heatmap (키: phase, 값: 2D numpy array)
aggregated_heatmaps = {}
number_of_per_phase = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

# 계산된 매치 데이터를 저장할 루트 폴더
calculated_matches_root = "calculated_matches"

# 여러 플레이어의 매치 데이터 순회
for player in player_names:
    try:
        player_url = f"https://api.pubg.com/shards/{PLATFORM}/players?filter[playerNames]={player}"
        player_data = fetch_json(player_url, HEADERS)
    except Exception as e:
        print(f"플레이어 {player} 데이터 가져오기 실패: {e}")
        continue

    # 플레이어별 저장 폴더 생성
    player_folder = os.path.join(calculated_matches_root, player)
    os.makedirs(player_folder, exist_ok=True)

    # 플레이어의 매치 목록 순회
    for match in player_data["data"][0]["relationships"]["matches"]["data"]:
        match_id = match["id"]

        # 각 매치별 저장 폴더 (이미 계산된 매치는 재활용)
        match_folder = os.path.join(player_folder, match_id)
        os.makedirs(match_folder, exist_ok=True)
        safety_zone_path = os.path.join(match_folder, "safety_zone_data.json")

        # 맵 및 게임 모드 필터링을 위해 매치 데이터 불러오기
        try:
            match_url = f"https://api.pubg.com/shards/{PLATFORM}/matches/{match_id}"
            match_data = fetch_json(match_url, HEADERS)
        except Exception as e:
            print(f"매치 {match_id} 데이터 가져오기 실패: {e}")
            continue

        map_name = match_data["data"]["attributes"]["mapName"]
        game_mode = match_data["data"]["attributes"]["gameMode"]
        if not (map_name == "Savage_Main" and (game_mode == "squad")):
            continue

        # 이미 계산된 매치라면 저장된 안전 구역 데이터를 불러오기
        if os.path.exists(safety_zone_path):
            try:
                with open(safety_zone_path, "r", encoding="utf-8") as f:
                    match_circle_data_json = json.load(f)
                # JSON에서 읽은 데이터의 키를 int, 값은 tuple로 변환
                match_circle_data = {int(k): tuple(v) for k, v in match_circle_data_json.items()}
                print(f"플레이어 {player}, 매치 {match_id} - 저장된 데이터를 불러옴.")
            except Exception as e:
                print(f"플레이어 {player}, 매치 {match_id} 저장 데이터 불러오기 실패: {e}")
                continue
        else:
            # 텔레메트리 URL 찾기
            telemetry_url = None
            for item in match_data["included"]:
                if item["type"] == "asset" and item["attributes"].get("name") == "telemetry":
                    telemetry_url = item["attributes"]["URL"]
                    break
            if telemetry_url is None:
                print(f"매치 {match_id}에서 텔레메트리 URL을 찾지 못했습니다.")
                continue

            try:
                telemetry_data = fetch_json(telemetry_url, HEADERS)
            except Exception as e:
                print(f"매치 {match_id} 텔레메트리 데이터 가져오기 실패: {e}")
                continue

            # 매치별 페이즈 안전구역 데이터 계산 (한 매치에서 각 페이즈마다 한 번씩 기록)
            match_circle_data = {}
            previous_radius = None
            current_phase = 0  # 초기 페이즈
            radius_count = 0   # 연속된 동일 반지름 카운트
            previous_phase_flag = False

            for event in telemetry_data:
                if event["_T"] == "LogGameStatePeriodic":
                    game_state = event.get("gameState", {})
                    radius = game_state.get("safetyZoneRadius")
                    if previous_radius is not None and radius == previous_radius:
                        radius_count += 1
                    else:
                        previous_phase_flag = True
                        radius_count = 0

                    if radius_count >= 1:
                        if previous_phase_flag:
                            current_phase += 1  # 새로운 페이즈
                            previous_phase_flag = False

                    previous_radius = radius

                    center_x = game_state["safetyZonePosition"]["x"]
                    center_y = game_state["safetyZonePosition"]["y"]

                    if current_phase not in match_circle_data:
                        match_circle_data[current_phase] = (center_x, center_y, radius)

            if not match_circle_data:
                print(f"매치 {match_id}에서 안전구역 데이터가 없습니다.")
                continue

            # 계산된 match_circle_data를 JSON으로 저장 (tuple은 list로 변환)
            try:
                match_circle_data_json = {str(k): list(v) for k, v in match_circle_data.items()}
                with open(safety_zone_path, "w", encoding="utf-8") as f:
                    json.dump(match_circle_data_json, f, ensure_ascii=False, indent=4)
                print(f"플레이어 {player}, 매치 {match_id} - 데이터 저장 완료.")
            except Exception as e:
                print(f"플레이어 {player}, 매치 {match_id} 데이터 저장 실패: {e}")
                continue

        # 각 페이즈별로 circle 데이터를 이미지 좌표계로 변환 후 누적
        for phase, circle in match_circle_data.items():
            x_img = int((circle[0] / MAP_SIZE) * IMG_SIZE)
            y_img = int((circle[1] / MAP_SIZE) * IMG_SIZE)
            r_img = int((circle[2] / MAP_SIZE) * IMG_SIZE)

            mask = np.zeros((IMG_SIZE, IMG_SIZE), dtype=np.float32)
            cv2.circle(mask, (x_img, y_img), r_img, 1, -1)

            if phase not in aggregated_heatmaps:
                aggregated_heatmaps[phase] = np.zeros((IMG_SIZE, IMG_SIZE), dtype=np.float32)
            aggregated_heatmaps[phase] += mask

            number_of_per_phase[phase] += 1

        print(f"플레이어 {player}, 매치 {match_id} 처리 완료.")

# 누적 heatmap 시각화 함수 (맵 이미지 오버레이)
def generate_phase_heatmap(phase, phase_heatmap, map_image_path, save_path="heatmaps/"):
    os.makedirs(save_path, exist_ok=True)
    
    # 맵 이미지 로드 및 크기 조정
    map_image = cv2.imread(map_image_path)
    map_image = cv2.resize(map_image, (IMG_SIZE, IMG_SIZE))
    
    # Heatmap 정규화
    if np.max(phase_heatmap) > 0:
        normalized_heatmap = np.uint8(255 * phase_heatmap / np.max(phase_heatmap))
    else:
        normalized_heatmap = np.uint8(phase_heatmap)
    
    # 컬러맵 적용 및 이미지 오버레이
    heatmap_colored = cv2.applyColorMap(normalized_heatmap, cv2.COLORMAP_JET)
    overlayed_image = cv2.addWeighted(map_image, 0.7, heatmap_colored, 0.5, 0)
    
    # 시각화 및 저장
    plt.figure(figsize=(6, 6))
    plt.imshow(cv2.cvtColor(overlayed_image, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.title(f"Aggregated Phase {phase} Heatmap (Sanhok)")
    plt.savefig(f"{save_path}sanhok_phase_{phase}_aggregated.png", bbox_inches="tight", pad_inches=0, dpi=300)
    plt.close()

# 누적 heatmap 시각화 실행
for phase, phase_heatmap in aggregated_heatmaps.items():
    if phase == 0:
        continue
    generate_phase_heatmap(phase, phase_heatmap, Sanhok_map_image_path)

print("✅ 각 페이즈별 누적 안전구역 heatmap이 저장되었습니다!")
print("각 페이즈별 데이터 건수:", number_of_per_phase)

###############################################################################
# 아래는 누적 heatmap에서 유용한 영역(최대값의 일정 임계값 이상인 영역)을 추출하는 함수입니다.
###############################################################################
def generate_useful_area(phase, phase_heatmap, map_image_path, save_path="useful_areas/", threshold_factor=0.5):
    os.makedirs(save_path, exist_ok=True)
    
    # 맵 이미지 로드 및 크기 조정
    map_image = cv2.imread(map_image_path)
    map_image = cv2.resize(map_image, (IMG_SIZE, IMG_SIZE))
    
    # Heatmap 정규화
    if phase_heatmap.max() > 0:
        norm_heatmap = phase_heatmap / phase_heatmap.max()
    else:
        norm_heatmap = phase_heatmap
    norm_heatmap_uint8 = (norm_heatmap * 255).astype(np.uint8)
    
    # 임계값 적용하여 유용한 영역 추출
    thresh_value = int(threshold_factor * 255)
    _, binary_mask = cv2.threshold(norm_heatmap_uint8, thresh_value, 255, cv2.THRESH_BINARY)
    
    # 형태 변환 (노이즈 제거)
    kernel = np.ones((3, 3), np.uint8)
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # 윤곽선 검출 및 오버레이, 
    # MODE: cv2.RETR_EXTERNAL, cv2.RETR_LIST, cv2.RETR_TREE  
    # METHOD: cv2.CHAIN_APPROX_SIMPLE, cv2.CHAIN_APPROX_TC89_L1, cv2.CHAIN_APPROX_TC89_KCOS
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    output_image = map_image.copy()
    cv2.drawContours(output_image, contours, -1, (0, 255, 0), 2)
    
    # 결과 저장
    output_image_path = os.path.join(save_path, f"sanhok_phase_{phase}_useful_overlay.png")
    cv2.imwrite(output_image_path, output_image)
    print(f"Phase {phase} 유용한 영역 추출 완료 (임계값: {thresh_value}).")

# 유용한 영역 추출 실행
for phase, phase_heatmap in aggregated_heatmaps.items():
    if phase == 0:
        continue
    generate_useful_area(phase, phase_heatmap, Sanhok_map_image_path, threshold_factor=0.35)

print("✅ 각 페이즈별 유용한 영역 추출 이미지가 저장되었습니다!")
