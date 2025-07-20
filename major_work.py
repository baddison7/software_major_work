import cv2, os, requests
import numpy as np

# def average_color_region(frame, center, size=3):
#     x, y = center
#     half = size // 2
#     region = frame[y - half:y + half + 1, x - half:x + half + 1]
#     return np.mean(region.reshape(-1, 3), axis=0)

# def is_scoreboard_visible(frame, red_coord, blue_coord, red_bgr, blue_bgr, tolerance=60):
#     red_avg = average_color_region(frame, red_coord)
#     blue_avg = average_color_region(frame, blue_coord)

#     def color_in_range(pixel, target_bgr):
#         return all(abs(int(pixel[i]) - target_bgr[i]) <= tolerance for i in range(3))

#     return color_in_range(red_avg, red_bgr) and color_in_range(blue_avg, blue_bgr)

def region_color_match(frame, region, target_bgr, tolerance=40, min_ratio=0.2):
    x, y, w, h = region
    roi = frame[y:y+h, x:x+w]

    lower = np.array([max(0, c - tolerance) for c in target_bgr])
    upper = np.array([min(255, c + tolerance) for c in target_bgr])

    mask = cv2.inRange(roi, lower, upper)
    ratio = np.sum(mask > 0) / (w * h)

    return ratio >= min_ratio


def has_timer_changed(prev_timer_roi_gray, curr_timer_roi_gray, threshold=1):
    if prev_timer_roi_gray is None:
        return True  # first frame considered changed
    diff = cv2.absdiff(curr_timer_roi_gray, prev_timer_roi_gray)
    diff_sum = np.sum(diff)
    return diff_sum >= threshold

def ocr_space_image_bytes(image_bytes):
    api_key = 'helloworld'
    response = requests.post(
        'https://api.ocr.space/parse/image',
        files={'image': ('frame.png', image_bytes)},
        data={'apikey': api_key, 'language': 'eng', 'isOverlayRequired': False}
    )
    result = response.json()
    # print("OCR API response:", result)  # <-- DEBUG PRINT
    try:
        return result['ParsedResults'][0]['ParsedText'].strip()
    except:
        return ""

# Video and region settings
video_path = 'screenRecording5.mov'
os.makedirs("frames", exist_ok=True)

red_bgr = (54, 45, 180)
blue_bgr = (157, 103, 50)

red_region = (1175, 1638, 170, 12)     # x, y, w, h
blue_region = (1535, 1638, 170, 12)
white_region = (1355, 1632, 170, 18)   # timer area or background
 
timer_x, timer_y, timer_w, timer_h = 1355, 1550, 175, 100
diff_threshold = 50000

cap = cv2.VideoCapture(video_path)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

prev_timer_roi_gray = None
frame_number = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_number += 500

    # Draw frame number on full frame
    cv2.putText(frame, f"Frame: {frame_number}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    scoreboard_visible = (
        region_color_match(frame, red_region, red_bgr, tolerance=40, min_ratio=0.2) and
        region_color_match(frame, blue_region, blue_bgr, tolerance=40, min_ratio=0.2) and
        region_color_match(frame, white_region, (230, 230, 230), tolerance=30, min_ratio=0.2)  # white = bright
    )

    if scoreboard_visible:
        timer_roi = frame[timer_y:timer_y+timer_h, timer_x:timer_x+timer_w]
        timer_roi_gray = cv2.cvtColor(timer_roi, cv2.COLOR_BGR2GRAY)
        timer_roi_gray = cv2.GaussianBlur(timer_roi_gray, (5,5), 0)

        if has_timer_changed(prev_timer_roi_gray, timer_roi_gray, diff_threshold):
            # Show full frame with rectangle
            cv2.imshow("Video Frame with ROI", frame)

            # Crop ROI and show it in separate window
            roi = frame[timer_y: timer_y + timer_h, timer_x: timer_x + timer_w]
            cv2.imwrite('frames/roi_frame_{}.png'.format(frame_number), roi)
            cv2.imshow("ROI Crop", roi)

            # Encode ROI as PNG bytes for OCR API
            _, buffer = cv2.imencode('.png', roi)
            image_bytes = buffer.tobytes()

            
            # OCR API call
            print('calling ORC API')
            # text = ocr_space_image_bytes(image_bytes)


        else:
            # print(f"[Frame {frame_number}] Timer unchanged, skipping processing.")
            pass

        prev_timer_roi_gray = timer_roi_gray
    else:
        # print(f"[Frame {frame_number}] Scoreboard not visible.")
        prev_timer_roi_gray = None  # reset timer diff if scoreboard disappears
        # roi = frame[timer_y: timer_y + timer_h, timer_x: timer_x + timer_w]
        # cv2.imwrite('not_visible/roi_frame_{}.png'.format(frame_number), frame)

cap.release()
cv2.destroyAllWindows()

