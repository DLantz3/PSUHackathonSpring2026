import cv2

# Create a VideoCapture object, 0 for default webcam
# Use 1 or higher for external cameras if you have multiple
cap = cv2.VideoCapture(0)

# Check if the webcam is opened correctly
if not cap.isOpened():
    print("Error: Could not open video source.")
    exit()

while True:
    # Read a frame from the webcam
    # ret is a boolean, True if frame was read successfully
    # frame is the actual image data (a NumPy array)
    ret, frame = cap.read()

    if not ret:
        print("End of video or error reading frame.")
        break

    # Display the captured frame
    cv2.imshow('Webcam Feed', frame)

    # Wait for 1 millisecond for a key press
    # If the 'q' key is pressed, break the loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and destroy all OpenCV windows
cap.release()
cv2.destroyAllWindows()

