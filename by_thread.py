from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
import selenium.common.exceptions as sel_sexceptions
from selenium.webdriver.firefox.webelement import FirefoxWebElement
# from bs4 import BeautifulSoup as bs
import time
from datetime import datetime as dt
# import concurrent.futures as cf
import threading
import logging

#logging setup
logging.basicConfig(filename="cookie.log", encoding="utf-8", level=logging.INFO, format="%(asctime)s %(message)s")


# this child class is unnecessary, since we are not modifying run()
class threadEx(threading.Thread):

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, daemon=None):
        super().__init__(group=group, target=target, name=name, daemon=daemon, args=args, kwargs=kwargs)

        self.target = target
        self.args = args
        self.kwargs = kwargs


    # def run(self):
    #     while True:
    #         if not self.event.is_set():
    #             self.__dict__['_target'](self.__dict__['_args'][0])
    #             # self._target(self._args[0])
    #         else: self.event.wait(1)

class value_of_argument_matched(object):
    def __init__(self, element: WebElement, attribute, value):
        self.element = element
        self.attribute = attribute
        self.value = value

    #when using it with the WebDriverWait.until, you need to supply 'driver', even if you dont use it.
    def __call__(self, driver):
        try:
            attr_value = self.element.get_attribute(self.attribute)
            if self.value in attr_value:
                return True
            else: return False
        except:
            return False



# def filter_avail_products(a_product: FirefoxWebElement) -> bool:
#     contents = a_product.get_attribute('class')
#     if "enabled" in contents: return True
#     else: return False
            
""" this function's goal is to divide the list of all products into two lists:
    1. products that can already be bought
    2. products that are unlocked but you need more money to buy them"""
def filter_products_into_lists(products: list) -> list:
    output_l = []
    ready_to_buy = []
    worth_waiting = []
    for product in products:
        attr = product.get_attribute('class')
        if "unlocked enabled" in attr:
            ready_to_buy.append(product)
        elif "unlocked disabled" in attr:
            worth_waiting.append(product)
        else:
            pass

    output_l.append(ready_to_buy)
    output_l.append(worth_waiting)
    return output_l # [[a,b,c,d,e], [f,g]]

def click_efficiently(cookie, event) -> None:
    event.set()
    while True:
        event.wait()
        cookie.click()
        time.sleep(0.1)

def buy_product(list_of_products: list, waittime: int, event: threading.Event, driver) -> None:
    event.set()
    while True:
        time.sleep(waittime)
        event.wait()
        possible_products = filter_products_into_lists(list_of_products)
        if len(possible_products[1]) == 0 and len(possible_products[0]) > 0:
            try:
                possible_products[0][-1].click()
            except sel_sexceptions.ElementNotInteractableException:
                pass
        #it will just check if the last worthwile is available to click (so technically, a cheaper worthwhile might be available, but it will skip over it)
        elif len(possible_products[1]) > 0:
            worthwhile_product = possible_products[1][-1]
            try: 
                WebDriverWait(driver, 10).until(value_of_argument_matched(worthwhile_product, 'class', "enabled"))
                worthwhile_product.click()
            except sel_sexceptions.TimeoutException:
                logging.info("sel_sexceptions.TimeoutException")
                possible_products = filter_products_into_lists(list_of_products)
                possible_products[0][-1].click()

#unlocked disabled

def driver_setup(**kwargs) -> WebDriver:
    fire_options = Options()
    fire_options.__dict__.update(kwargs)
    driver = webdriver.Firefox(options=fire_options)
    if not fire_options.headless: driver.maximize_window()
    return driver
    

def main():

    driver = driver_setup(headless=False)
    
    driver.get("https://orteil.dashnet.org/cookieclicker/")

    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="bigCookie"]')))

    cookie = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div[15]/div[8]/div[1]")))


    """ Ok. Now i think i get it. (OBSOLETE. sorta)
        In this particular instance you need to create just one thread, and that is your clicker process.
        Before that, you need to make a threadEx class that would allow you to stop and start a thread provided you have
        a reference to that thread (a threadEx object). This object needs to have a "run" method that will check if an internal
        flag signaling the thread's stop is set. If this flag is not set, the program runs normally, but with every iteration
        of its while loop (or any other loop) it checks if this flag has been set at the very beginning of the iteration.
        If the flag is set (threads.Event().set()) the condition in this loop is met and Event().wait() is executed. The switching
        of this thread can (and maybe has to) take place outside the thread"""
    
    """ Alternatively, and that might just be the better option:
        Your function, that will become the thread's action (click_efficiently in our example) needs to accept one extra argument, and
        that is and Event object. This Event needs(?) to be defined and modified outside of the cookie thread. The clicker function
        upon which the thread relies needs to be modified so that the thread waits if the Event is not set and runs normally if the Event is set.
        Event().wait() does not wait if Event() is set to True, but waits when it is set to False"""

    """ To find all the product elements (the upgrades) you need to use the method presented here:
        (https://www.tutorialspoint.com/what-is-following-sibling-in-selenium). Simply, you need to find a way to loop through all
        the siblings and append them to a list. A loop-stopping condition in this case could be an exception handled by try/except - if an
        exception indicating going out of range is detected, stop iterating and return the list of siblings.
        Proposed exception: selenium.common.exceptions.NoSuchElementException """

    
    list_of_products = []
    break_condition = False
    iteration = 1

    list_of_products.append(driver.find_element_by_xpath(f"//*[@id='product0']")) # first element needs to be added manually, because iteration=0 doesnt work
    while not break_condition:
        try:
            sibling = driver.find_element_by_xpath(f"//*[@id='product0']/following-sibling::div[{iteration}]")
        except sel_sexceptions.NoSuchElementException:
            break_condition = True
        else:
            list_of_products.append(sibling)
            iteration += 1

    eve = threading.Event()

    t1 = threadEx(target=click_efficiently, args=[cookie, eve])
    t1.setDaemon(True) # Deamon - subthread will die once non-daemons and main die.
    t1.start()

    # t11 = threadEx(target=click_efficiently, args=[cookie, eve])
    # t11.setDaemon(True) # Deamon - subthread will die once non-daemons and main die.
    # t11.start()

    t2 = threadEx(target=buy_product, args=[list_of_products, 15, eve, driver])
    t2.setDaemon(True)
    t2.start()

    while True:
        inp = input("start/stop/end: ")
        if inp == "start":
            eve.set()
        if inp == "stop":
            eve.clear()
        if inp == "end":
            break

    
    #additional clear at the end so that the thread terminates.
    eve.clear()
    # t1.join()
    # t2.join()

    driver.quit()

if __name__ == "__main__":
    main()
