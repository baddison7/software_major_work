import cv2, os, requests, re, hashlib
import numpy as np
# import keras_ocr

# ocr_pipeline = keras_ocr.pipeline.Pipeline()

# checks if regoin matches the target color within a tolerance
def region_color_match(frame, region, target_bgr, tolerance=40, min_ratio=0.2):
    x, y, w, h = region
    roi = frame[y:y+h, x:x+w]

    lower = np.array([max(0, c - tolerance) for c in target_bgr])
    upper = np.array([min(255, c + tolerance) for c in target_bgr])

    mask = cv2.inRange(roi, lower, upper)
    ratio = np.sum(mask > 0) / (w * h)

    return ratio >= min_ratio


# if timer frame has changed significantly since last frame
def has_timer_changed(prev_timer_roi_gray, curr_timer_roi_gray, threshold=2):
    if prev_timer_roi_gray is None:
        return True  # true if no previous frame
    diff = cv2.absdiff(curr_timer_roi_gray, prev_timer_roi_gray)
    return np.sum(diff) >= threshold

# takes an in ROI, caches it and returns the text in it
def ocr_space_image_bytes(roi):
    _, buffer = cv2.imencode('.png', roi) # Encode ROI as PNG bytes for OCR API
    image_bytes = buffer.tobytes()
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, roi_bw = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    key = hashlib.md5(roi_bw.tobytes()).hexdigest()
    if key in ocr_cache:
        print('cache hit')
        return ocr_cache[key]
    
    # text = input('read text: ')  # For testing, replace with read_timer() in production
    # if text:
    #     return text
    response = requests.post(
        'https://api.ocr.space/parse/image',
        files={'image': ('frame.png', image_bytes)},
        data={'apikey': 'helloworld', 'language': 'eng', 'isOverlayRequired': False}
    )
    result = response.json()
    try:
        text = result['ParsedResults'][0]['ParsedText'].strip()
        ocr_cache[key] = text
    except Exception as e:
        print(f"OCR Error: {e} — Not caching")
        text = ""
    
    return text

# def ocr_keras_image(roi):
#     # keras-ocr expects RGB images, not BGR
#     roi_rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
#     predictions = ocr_pipeline.recognize([roi_rgb])
#     texts = [text for text, box in predictions[0]]
#     return '\n'.join(texts)

def parse_score_text(text):
    lines = [re.sub(r'[^\d\w\s]', '', line).strip() for line in text.strip().splitlines() if line.strip()]
    match = re.match(r'(\w+)\s+(\d+)', lines[0])
    if not match: raise ValueError("Invalid match info line")
    match_type, match_number = match.group(1), int(match.group(2))
    team_numbers = [int(line) for line in lines[1:] if line.isdigit()]
    if len(team_numbers) < 6: raise ValueError("Not enough team numbers found")
    return {
        "type": match_type,
        "number": match_number,
        "teams": [team_numbers[:3], team_numbers[3:6]]
    }

class Match:
    def __init__(self, type, number, players, frame, timestamp):
        self.type = type
        self.number = number
        self.players = players
        self.frame = frame
        self.timestamp = timestamp

    def __repr__(self):
        return f"{self.type} {self.number} @ frame {self.frame} — {self.players}"

class recording4:
    def __init__(self):
        self.video_path = 'screenRecording4.mov'
        self.start_frame = 1
        self.red_region = (1175, 1638, 170, 12)
        self.blue_region = (1535, 1638, 170, 12)
        self.white_region = (1355, 1632, 170, 18)
        self.timer_x, self.timer_y, self.timer_w, self.timer_h = 1355, 1550, 175, 100
        self.quali_x, self.quali_y, self.quali_w, self.quali_h = 675, 1475, 1550, 200

class videolong:
    def __init__(self):
        self.video_path = 'videoplayback720Long.mp4'
        self.start_frame = 500000
        self.red_region = 522, 677, 76, 5
        self.blue_region = 682, 677, 76, 5
        self.white_region = 602, 675, 76, 7
        self.white_left_region = 602, 642, 7, 40
        self.white_right_region = 670, 642, 7, 40
        self.zero_region = 659, 657, 5, 12
        self.timer_x, self.timer_y, self.timer_w, self.timer_h = 601, 642, 77, 40
        self.quali_x, self.quali_y, self.quali_w, self.quali_h = 300, 607, 680, 80
    
def get_timer_roi(frame):    
    return frame[video.timer_y:video.timer_y+video.timer_h, video.timer_x:video.timer_x+video.timer_w]

def get_quali_roi(frame):    
    return frame[video.quali_y:video.quali_y+video.quali_h, video.quali_x:video.quali_x+video.quali_w]

video = videolong()
video_path = video.video_path

cap = cv2.VideoCapture(video_path)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

os.makedirs("timer", exist_ok=True)
os.makedirs("auto", exist_ok=True)
os.makedirs("quali", exist_ok=True)

red_bgr = (54, 45, 180)
blue_bgr = (157, 103, 50)

frame_number = 500000
count_down = 0
prev_timer_roi_gray = None
diff_threshold = 8500 # false positves at 7500
matches = []

cap.set(cv2.CAP_PROP_POS_FRAMES, video.start_frame)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
ocr_cache = {}    

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_number += 1

    if count_down > 0:
        count_down -= 1
        continue

    if frame_number % 5 != 0:
        continue
    

    scoreboard_visible = (
        region_color_match(frame, video.red_region, red_bgr, tolerance=40, min_ratio=0.2) and
        region_color_match(frame, video.blue_region, blue_bgr, tolerance=40, min_ratio=0.2) and
        region_color_match(frame, video.white_region, (230, 230, 230), tolerance=20, min_ratio=0.2) and
        region_color_match(frame, video.white_left_region, (230, 230, 230), tolerance=20, min_ratio=0.2) and
        region_color_match(frame, video.white_right_region, (230, 230, 230), tolerance=20, min_ratio=0.2)
    )

    if scoreboard_visible:
        timer_roi = get_timer_roi(frame)
        timer_roi_bw = cv2.GaussianBlur(cv2.cvtColor(timer_roi, cv2.COLOR_BGR2GRAY), (5,5), 0)

        if has_timer_changed(prev_timer_roi_gray, timer_roi_bw, diff_threshold):
            if region_color_match(frame, video.zero_region, (255, 255, 255), tolerance=30, min_ratio=0.2) == False:
                cv2.imwrite('timer/roi_frame_{}.png'.format(frame_number), timer_roi)

                timer = ocr_space_image_bytes(timer_roi)
                # print(f'keras orc: {ocr_keras_image(timer_roi)}')
                print(f'timer orc: {timer}')
                timer = '0:14'
                print(f"[Frame {frame_number}] timer Result: {timer}")
                print(f'timestamp: {frame_number / fps}')
                count_down = 4600
                
                quali_roi = get_quali_roi(frame)
                cv2.imwrite('quali/roi_frame_{}.png'.format(frame_number), quali_roi)
                # text = ocr_space_image_bytes(quali_roi)
                # info = parse_score_text(text)
                # matches.append(Match(info['type'], info['number'], info['teams'], frame_number, 'XXX'))
            else:
                cv2.imwrite('auto/roi_frame_{}.png'.format(frame_number), timer_roi)

        prev_timer_roi_gray = timer_roi_bw
    else:
        prev_timer_roi_gray = None  # reset timer diff if scoreboard disappears

cap.release()