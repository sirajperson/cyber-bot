import logging
import time
import sys
import os
import asyncio

from src.common.config import Config
from selenium.webdriver.common.by import By
from src.viewers.navigator import Navigator
from src.controllers.graph_controller import GraphController

# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(filename='../logs/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


async def main():
    logging.info("Starting Cyber Bot")
    navigator = Navigator()

    try:
        # Authenticate Session
        navigator.authenticate(Config.USERNAME, Config.PASSWORD)

        # Navigate to dashboard.
        dashboard_link = navigator.find_element(By.XPATH, "/html/body/div/div/div/div/div/div/div/div[1]/div/a[1]")
        if dashboard_link: dashboard_link.click(); time.sleep(2)

        # Here I used the XPath because it was easiest to get the element that way. CyberSkyline isn't using iframes.
        enter_button = navigator.find_element(By.XPATH, "/html/body/div/div/div/div/div/div/div/div[2]/div/div[1]/div/div/div/div/div[2]/div/div[4]/a")
        if enter_button: enter_button.click(); time.sleep(3); logging.info("Entered Gymnasium")

        # Here, we execute the graph_controller.
        graph_controller = GraphController()
        await graph_controller.organize_teams(navigator)

    except Exception as e:
        logging.error("Error: %s", str(e))
    finally:
        navigator.close_browser()
        logging.info("Bot execution completed")


if __name__ == "__main__":
    asyncio.run(main())