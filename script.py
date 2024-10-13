import os
import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By

browser = webdriver.Chrome()

browser.get('https://www.spotify.com/account/overview/')

load_dotenv()

browser.find_element(By.ID, 'login-username').send_keys(os.getenv("EMAIL"))

browser.find_element(By.ID, 'login-password').send_keys(os.getenv("PASSWORD"))

browser.find_element(By.ID, 'login-button').click()

browser.implicitly_wait(15)

browser.find_element(By.XPATH, '//*[@id="menu-group-subscription"]/a[3]/div[1]').click()

frame = browser.find_element(By.ID, 'family-web-iframe')

users = ["//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[2]/a",
         "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[3]/a",
         "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[4]/a",
         "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[5]/a",
         "//*[@id=""__next""]/main/div[2]/div/section/div[1]/ul/li[6]/a"]
time.sleep(5)
time.sleep(1)

