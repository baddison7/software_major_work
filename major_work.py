import cv2, os, requests
import numpy as np


def is_scoreboard_visible(frame, red_coord, blue_coord, red_bgr, blue_bgr, tolerance=40):
    red_pixel = frame[red_coord[1], red_coord[0]]
    blue_pixel = frame[blue_coord[1], blue_coord[0]]
    def color_in_range(pixel, target_bgr):
        return all(abs(int(pixel[i]) - target_bgr[i]) <= tolerance for i in range(3))
    return color_in_range(red_pixel, red_bgr) and color_in_range(blue_pixel, blue_bgr)

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

red_coord = (1175, 1560)
blue_coord = (1695, 1560)
red_bgr = (54, 45, 180)
blue_bgr = (157, 103, 50)
tolerance = 50

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
    frame_number += 10

    # Draw frame number on full frame
    cv2.putText(frame, f"Frame: {frame_number}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    if is_scoreboard_visible(frame, red_coord, blue_coord, red_bgr, blue_bgr, tolerance):
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
        print(f"[Frame {frame_number}] Scoreboard not visible.")
        prev_timer_roi_gray = None  # reset timer diff if scoreboard disappears
        roi = frame[timer_y: timer_y + timer_h, timer_x: timer_x + timer_w]
        cv2.imwrite('not_visible/roi_frame_{}.png'.format(frame_number), frame)

cap.release()
cv2.destroyAllWindows()

