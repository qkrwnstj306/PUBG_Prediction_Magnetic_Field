import keyboard
import time
import obsws_python as obs

# 🔹 OBS WebSocket 연결 설정
OBS_HOST = "localhost"
OBS_PORT = 4455
SCENE_NAME = "장면"  # OBS에서 히트맵이 있는 씬 이름 설정

# 🔹 OBS WebSocket 클라이언트 연결
client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT)

# 🔹 히트맵 오버레이 설정
HEATMAP_SOURCE_NAME = "heatmap"  # OBS에서 추가한 소스 이름
HEATMAP_IMAGE_PATH = r"C:\Users\mki73\OneDrive\Desktop\workspace\vscode\codingTest\pubg\useful_areas\sanhok_phase_7_useful_overlay.png"

def get_heatmap_item_id():
    """OBS에서 히트맵 소스의 scene_item_id 가져오기"""
    scene_data = client.get_scene_item_list(SCENE_NAME)  # 🔹 반환값이 Dataclass 객체
    scene_items = scene_data.scene_items  # ✅ 올바르게 Dataclass 속성 접근

    print("🔹 scene_items 내용:", scene_items)  # 🔹 디버깅용 출력

    for item in scene_items:
        print("🔹 item:", item)  # 🔹 각 아이템의 구조를 출력
        if item.get('sourceName') == HEATMAP_SOURCE_NAME:  # `get()` 사용하여 키가 없는 경우에도 에러 발생하지 않음
            return item['sceneItemId']
    return None  # 찾지 못한 경우

def set_heatmap_visibility(visible=True):
    """OBS에서 히트맵 소스의 가시성을 변경하는 함수"""
    heatmap_item_id = get_heatmap_item_id()
    if heatmap_item_id is None:
        print(f"❌ '{HEATMAP_SOURCE_NAME}' 소스를 찾을 수 없습니다!")
        return

    # overlay 파라미터를 정확하게 전달
    overlay = {
        "file": HEATMAP_IMAGE_PATH,
        # 추가 설정이 필요하다면 여기에 다른 항목들을 추가해 주세요
    }
    
    client.set_input_settings(HEATMAP_SOURCE_NAME, overlay)  # 두 번째 인자 추가
    client.set_scene_item_enabled(SCENE_NAME, heatmap_item_id, visible)
    print(f"🔹 '{HEATMAP_SOURCE_NAME}' 소스를 {'활성화' if visible else '비활성화'} 했습니다.")

def toggle_heatmap():
    """맵 키 (M)를 누를 때마다 히트맵 오버레이 ON/OFF"""
    heatmap_item_id = get_heatmap_item_id()
    if heatmap_item_id is None:
        print(f"❌ '{HEATMAP_SOURCE_NAME}' 소스를 찾을 수 없습니다!")
        return

    heatmap_visible = client.get_scene_item_enabled(SCENE_NAME, heatmap_item_id)
    set_heatmap_visibility(not heatmap_visible)  # 현재 상태의 반대 값 적용
    print(f"🔹 Heatmap {'ON' if not heatmap_visible else 'OFF'}")

# 🔹 키 입력 감지 (M키 누르면 히트맵 토글)
keyboard.add_hotkey("m", toggle_heatmap)

print("🔹 배틀그라운드에서 M키를 누르면 히트맵이 오버레이됩니다!")
while True:
    time.sleep(1)  # 실행 유지
