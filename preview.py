import cv2

# === CONFIG ===
video_path = "screenRecording4.mov"  # <-- change if needed
frame_to_show = 0  # choose which frame to extract

# === Load frame ===
cap = cv2.VideoCapture(video_path)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

if frame_to_show >= total_frames:
    print(f"Error: Frame {frame_to_show} exceeds total frame count {total_frames}")
    exit()

cap.set(cv2.CAP_PROP_POS_FRAMES, frame_to_show)
ret, frame = cap.read()
cap.release()

if not ret:
    print("Failed to load frame.")
    exit()

print(f"Loaded frame {frame_to_show}. Image size: {frame.shape[1]}x{frame.shape[0]} (W x H)")

# === Main loop for user input ===
while True:
    try:
        raw = input("Enter region as x,y,width,height (or 'q' to quit): ").strip()
        if raw.lower() == 'q':
            break

        x, y, w, h = map(int, raw.split(','))
        roi = frame[y:y+h, x:x+w]

        if roi.size == 0:
            print("Invalid region. Nothing to show.")
            continue

        # Draw the region on the full frame for context
        frame_copy = frame.copy()
        cv2.rectangle(frame_copy, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imshow("Full Frame (region highlighted)", frame_copy)
        cv2.imshow("Region Crop", roi)

        print(f"Showing region x:{x}, y:{y}, w:{w}, h:{h}")
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    except ValueError:
        print("Invalid format. Please enter 4 integers separated by commas.")
    except Exception as e:
        print(f"Error: {e}")

# red   bottom 1175,1638,170,12
# blue  bottom 1535,1638,170,12
# white bottom 1355,1632,170,18

# quali number 950,1490,975,60
# short number 1150,1490,600,60

# team numbers 675,1550,1550,100
# blue team    1710,1585,430,50
# red team     740,1585,425,50