import cv2, os, requests, re, hashlib
import numpy as np

def region_color_match(frame, region, target_bgr, tolerance=40, min_ratio=0.2):
    x, y, w, h = region
    roi = frame[y:y+h, x:x+w]

    lower = np.array([max(0, c - tolerance) for c in target_bgr])
    upper = np.array([min(255, c + tolerance) for c in target_bgr])

    mask = cv2.inRange(roi, lower, upper)
    ratio = np.sum(mask > 0) / (w * h)

    return ratio >= min_ratio

def has_timer_changed(prev_timer_roi_gray, curr_timer_roi_gray, threshold=2):
    if prev_timer_roi_gray is None:
        return True  # first frame considered changed
    diff = cv2.absdiff(curr_timer_roi_gray, prev_timer_roi_gray)
    return np.sum(diff) >= threshold

def ocr_space_image_bytes(image_bytes):
    key = hashlib.md5(image_bytes).hexdigest()
    if key in ocr_cache:
        print('cache hit')
        return ocr_cache[key]
    
    response = requests.post(
        'https://api.ocr.space/parse/image',
        files={'image': ('frame.png', image_bytes)},
        data={'apikey': 'helloworld', 'language': 'eng', 'isOverlayRequired': False}
    )
    result = response.json()
    try:
        text = result['ParsedResults'][0]['ParsedText'].strip()
    except:
        text = ""
    ocr_cache[key] = text
    return text

def read_timer():
    roi = frame[timer_y: timer_y + timer_h, timer_x: timer_x + timer_w]
    cv2.imwrite('frames/roi_frame_{}.png'.format(frame_number), roi)
    
    # timer = input('read timer: ')  # For testing, replace with read_timer() in production
    # return timer
    # Encode ROI as PNG bytes for OCR API
    _, buffer = cv2.imencode('.png', roi)
    return ocr_space_image_bytes(buffer.tobytes())


def read_quali():
    # quali_x, quali_y, quali_w, quali_h = 675, 1475, 1550, 200
    quali_x, quali_y, quali_w, quali_h = 300, 607, 680, 80
    roi = frame[quali_y: quali_y + quali_h, quali_x: quali_x + quali_w]
    cv2.imwrite('quali/roi_frame_{}.png'.format(frame_number), roi)

    # Encode ROI as PNG bytes for OCR API
    _, buffer = cv2.imencode('.png', roi)
    return ocr_space_image_bytes(buffer.tobytes())

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
reference_timer_image = None  # global or outer scope
def is_timer_same_as_reference(curr_timer_roi_gray, threshold=1000):
    global reference_timer_image
    if reference_timer_image is None:
        return False
    diff = cv2.absdiff(reference_timer_image, curr_timer_roi_gray)
    return np.sum(diff) < threshold

class Match:
    def __init__(self, type, number, players, frame, timestamp):
        self.type = type
        self.number = number
        self.players = players
        self.frame = frame
        self.timestamp = timestamp

    def __repr__(self):
        return f"{self.type} {self.number} @ frame {self.frame} — {self.players}"

# Video and region settings
# video_path = 'screenRecording4.mov'
video_path = 'videoplayback720Long.mp4'
cap = cv2.VideoCapture(video_path)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

os.makedirs("frames", exist_ok=True)
os.makedirs("quali", exist_ok=True)

red_bgr = (54, 45, 180)
blue_bgr = (157, 103, 50)


# red_region = (1175, 1638, 170, 12)
# blue_region = (1535, 1638, 170, 12)
# white_region = (1355, 1632, 170, 18)
red_region = 522, 677, 76, 5
blue_region = 682, 677, 76, 5
white_region = 602, 675, 76, 7

# timer_x, timer_y, timer_w, timer_h = 1355, 1550, 175, 100
timer_x, timer_y, timer_w, timer_h = 601, 642, 77, 40

frame_number = 0
start_frame = 500000
count_down = 0
prev_timer_roi_gray = None
diff_threshold = 7500
matches = []

cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
ocr_cache = {}    

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_number += 1

    if frame_number % 5 != 0:
        continue
    

    scoreboard_visible = (
        region_color_match(frame, red_region, red_bgr, tolerance=40, min_ratio=0.2) and
        region_color_match(frame, blue_region, blue_bgr, tolerance=40, min_ratio=0.2) and
        region_color_match(frame, white_region, (230, 230, 230), tolerance=30, min_ratio=0.2)
    )

    if scoreboard_visible:
        timer_roi = frame[timer_y:timer_y+timer_h, timer_x:timer_x+timer_w]
        timer_roi_gray = cv2.GaussianBlur(cv2.cvtColor(timer_roi, cv2.COLOR_BGR2GRAY), (5,5), 0)

        if has_timer_changed(prev_timer_roi_gray, timer_roi_gray, diff_threshold):
            roi = frame[timer_y: timer_y + timer_h, timer_x: timer_x + timer_w]
            cv2.imwrite('frames/roi_frame_{}.png'.format(frame_number), roi)
            if count_down <= 0:
                timer = read_timer()
                print(f"[Frame {frame_number}] timer Result: {timer}")
                if timer == '0:14':
                    count_down = 148 #normal 147 could be 148 to be risky
                    print(f"[Frame {frame_number}] Count down started: {count_down} frames")
                    text = read_quali()
                    print(text)
                    # info = parse_score_text(text)
                    # matches.append(Match(info['type'], info['number'], info['teams'], frame_number, 'XXX'))
            else:
                count_down -= 1
                print(f"[Frame {frame_number}] Count down: {count_down} frames remaining")
            found = True      
        else:
            pass

        prev_timer_roi_gray = timer_roi_gray
    else:
        prev_timer_roi_gray = None  # reset timer diff if scoreboard disappears
        if found == True:
            print(f"[Frame {frame_number}] No scoreboard detected.")
            found = False
        if not scoreboard_visible and frame_number % 500 == 0:
            cv2.imwrite(f"missing_scoreboard/roi_frame_{frame_number}.png", frame)

cap.release()
# print(matches)