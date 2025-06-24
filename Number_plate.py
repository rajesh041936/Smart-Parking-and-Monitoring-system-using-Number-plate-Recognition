import cv2
import os
import numpy as np
import pytesseract
import re
import sqlite3
from datetime import datetime

def detect_and_extract_number_plate(image_path):
    harcascade = "model/haarcascade_russian_plate_number.xml"
    plate_cascade = cv2.CascadeClassifier(harcascade)

    img = cv2.imread(image_path)

    if img is None:
        print("Error: Could not load image.")
        exit()

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    img_gray = cv2.GaussianBlur(img_gray, (5, 5), 0)

    plates = plate_cascade.detectMultiScale(img_gray, 1.1, 4)

    os.makedirs("plates", exist_ok=True)

    min_area = 500
    count = 0
    plate_mask = np.zeros_like(img)  

    for (x, y, w, h) in plates:
        area = w * h
        if area > min_area:
            img_roi = img[y:y + h, x:x + w]

            plate_mask[y:y + h, x:x + w] = img[y:y + h, x:x + w]

            filename = os.path.join("plates", f"plate_only_{count}.jpg")
            cv2.imwrite(filename, plate_mask)
            print(f"Plate saved: {filename}")

            count += 1

    if count == 0:
        print("No plates detected.")
        return None

    img = cv2.imread("plates/plate_only_0.jpg")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite("processed.jpg", gray)

    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    text = pytesseract.image_to_string(gray, config='--psm 7')
    clean_text = re.sub(r'[^A-Za-z0-9]', '', text)

    return clean_text

def initialize_database():
    conn = sqlite3.connect('slot_booking.db')
    cursor = conn.cursor()

    # Create users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phnumber TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Create bookings table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            slot_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            in_time TEXT NOT NULL,
            out_time TEXT NOT NULL,
            vehicle_number TEXT NOT NULL,
            mobile_number TEXT NOT NULL,
            status TEXT DEFAULT 'available',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized successfully.")

def match_with_database(extracted_text):
    if not extracted_text:
        print("No text extracted from the number plate.")
        return

    conn = sqlite3.connect('slot_booking.db')
    cursor = conn.cursor()

    extracted_text_clean = extracted_text.replace(" ", "")

    cursor.execute('SELECT vehicle_number, date, in_time, out_time FROM bookings')
    bookings = cursor.fetchall()

    current_datetime = datetime.now()
    current_date = current_datetime.strftime('%Y-%m-%d')
    current_time = current_datetime.strftime('%H:%M')

    match_found = False

    for booking in bookings:
        vehicle_number, date, in_time, out_time = booking

        vehicle_number_clean = vehicle_number.replace(" ", "")

        print(f"Database Vehicle Number: {vehicle_number_clean}, Extracted Text: {extracted_text_clean}")

        if extracted_text_clean == vehicle_number_clean:
            print(f"Match found for vehicle number: {vehicle_number}")

            if date == current_date:
                print(f"Date matched: {date}")

                if in_time <= current_time <= out_time:
                    print(f"Current time {current_time} is within the range {in_time} to {out_time}.")
                    match_found = True
                else:
                    print(f"Current time {current_time} is NOT within the range {in_time} to {out_time}.")
            else:
                print(f"Date does not match. Database date: {date}, Current date: {current_date}")
        else:
            print(f"No match for vehicle number: {vehicle_number}")

    if not match_found:
        print("No matching vehicle number found in the database or date/time mismatch.")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    initialize_database()

    image_path = "image1.jpg"

    extracted_text = detect_and_extract_number_plate(image_path)
    print("Extracted Text:", extracted_text)

    match_with_database(extracted_text)