from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
import time

edge_opts = Options()
edge_opts.add_argument('--headless=new')
edge_opts.add_argument('--no-sandbox')
edge_opts.add_argument('--disable-gpu')
edge_opts.add_argument('--window-size=800,1200')
edge_opts.add_argument('--force-device-scale-factor=2')

driver = webdriver.Edge(options=edge_opts)

html_path = r'C:\Users\DELL LATITUDE 5520\.openclaw\workspace\poster.html'
driver.get('file:///C:/Users/DELL%20LATITUDE%205520/.openclaw/workspace/poster.html')
time.sleep(3)

# Get full page height
total_height = driver.execute_script("return document.body.scrollHeight")
driver.set_window_size(800, total_height)
time.sleep(1)

out_path = r'C:\Users\DELL LATITUDE 5520\.openclaw\workspace\poster.png'
driver.save_screenshot(out_path)
print(f"DONE: {out_path}")
driver.quit()
