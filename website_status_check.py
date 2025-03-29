import pandas as pd
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pygame  # ✅ NEW: More reliable sound module

# File path
file_path = "IOM-Data-Scrup.csv"

# Load CSV
df = pd.read_csv(file_path, low_memory=False)

# Ensure the status column exists
if "Website status" not in df.columns:
    df["Website status"] = ""

# Function to check website status
def check_website_status(index, url, start_time):
    elapsed = int(time.time() - start_time)
    elapsed_min = elapsed // 60
    elapsed_sec = elapsed % 60
    timer_display = f"⏱ Elapsed: {elapsed_min:02d}:{elapsed_sec:02d}"

    if pd.isna(url) or str(url).strip() == "":
        status = "No URL"
    else:
        if not str(url).startswith("http"):
            url = "http://" + str(url)
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                status = "Active"
            else:
                status = f"Down ({response.status_code})"
        except requests.exceptions.RequestException:
            status = "Down"

    # Update in dataframe
    df.at[index, "Website status"] = status
    df.to_csv(file_path, index=False)  # Save after each check
    print(f"[{index+1}/{len(df)}] {url} ➜ {status} | {timer_display}")
    return status

# Function to play sound
def play_completion_sound():
    try:
        pygame.init()
        pygame.mixer.init()
        pygame.mixer.music.load("static/done.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.5)
    except Exception as e:
        print(f"⚠️ Could not play sound: {e}")
    finally:
        pygame.quit()

# Main function
def main():
    print("🔍 Checking website statuses (updates after each check)...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(check_website_status, idx, row["company_domain"], start_time)
            for idx, row in df.iterrows()
        ]

        for future in as_completed(futures):
            future.result()  # Just to raise exceptions if any

    print("✅ All websites checked and saved!")
    play_completion_sound()  # ✅ Plays the final sound after all checks

if __name__ == "__main__":
    main()
