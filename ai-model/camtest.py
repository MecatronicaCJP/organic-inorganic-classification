import cv2

for i in range(5):
    cam = cv2.VideoCapture(i)
    if cam.isOpened():
        ok, frame = cam.read()
        if ok:
            print(f"indice {i}: OK  ({frame.shape[1]}x{frame.shape[0]})")
        else:
            print(f"indice {i}: abre pero no lee frames")
        cam.release()
    else:
        print(f"indice {i}: no disponible")