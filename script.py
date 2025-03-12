import os
import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

browser = webdriver.Chrome()

browser.get('https://www.spotify.com/account/overview/')

load_dotenv()

browser.find_element(By.ID, 'login-username').send_keys(os.getenv("EMAIL"))

browser.find_element(By.ID, 'login-password').send_keys(os.getenv("PASSWORD"))

browser.find_element(By.ID, 'login-button').click()

menu_group_button =  "/html/body/div[1]/div[1]/div/div[2]/div/div[4]/div[3]/a[3]"

WebDriverWait(browser, 5).until(expected_conditions.element_to_be_clickable((By.XPATH, menu_group_button))).click()

frame = browser.find_element(By.ID, 'family-web-iframe')

time.sleep(5)

users = ["//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[2]/a",
         "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[3]/a",
         "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[4]/a",
         "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[5]/a",
         "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[6]/a"]

def turn_off_explicit_songs(user_id):
    user_buttons = {
        1: "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[2]/a",
        2: "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[3]/a",
        3: "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[4]/a",
        4: "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[5]/a",
        5: "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[6]/a"
    }

    button_xpath = user_buttons.get(user_id)
    if button_xpath:
        WebDriverWait(browser, 5).until(expected_conditions.element_to_be_clickable((By.XPATH, button_xpath))).click()

if __name__ == "__main__":
    conn = sqlite3.connect("/home/ilie/PycharmProjects/SpotifyFamily/spotify_family.db")
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM users WHERE debt > 0")
    users_with_debt = cursor.fetchall()
    conn.close()

    for user in users_with_debt:
        turn_off_explicit_songs(user[0])
