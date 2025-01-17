from selenium import webdriver
from selenium.webdriver.common import keys
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, ElementNotVisibleException
import time
import os
from urllib.parse import quote_plus

from selenium.webdriver.remote.webelement import WebElement


driver = webdriver.Chrome()                     # Needs to be global for all classes to use
driver.get('https://web.whatsapp.com')


MESSAGE_BUBBLE_CLASS_NAME = "_2x4bz"            # !!! Update this if the bot stops working, means Whatsapp have changed
                                                # the class attribute names
MESSAGE_CLICK_BUTTON = "_1E0Oz"                  # For some reason the ENTER key doesnt work, so we use this to click the button in Whatsapp instead.

class BotConfig(object):
    # Input: Contact list
    last_msg = False
    last_msg_id = False

    command_history = []
    last_command = ""

    def __init__(self, contact_list):
        self.contacts = contact_list

    def get_contacts(self):
        return self.contacts

    def set_last_chat_message(self, msg, time_id):
        # Given a message and its ID, set the attributes in the Config to said message and ID
        self.last_msg = msg
        self.last_msg_id = time_id

    def get_last_chat_message(self):
        # return msg and id
        return self.last_msg, self.last_msg_id

    def set_last_command(self, command):
        self.last_command = command
        self.command_history.append(command)

    def get_command_history(self):
        return "You have asked the following commands: " + ", ".join(self.command_history)


class Bot(object):
    def __init__(self):
        # gets whatsapp contacts and initialises it in config
        self.config = BotConfig(contact_list=whatsapp_contacts())
        self.init_bot()

    def init_bot(self):
        while True:
            # calls poll chat function permanently
            self.poll_chat()

    def poll_chat(self):
        last_msg = chat_history()

        if last_msg:
            time_id = time.strftime('%H-%M-%S', time.gmtime())

            # Gets message and msg_id from config
            last_saved_msg, last_saved_msg_id = self.config.get_last_chat_message()

            # Compare saved message and id to current given message and id
            if last_saved_msg != last_msg and last_saved_msg_id != time_id:
                # If not the same, overwrite last message and id in config
                
                self.config.set_last_chat_message(msg=last_msg, time_id=time_id)

                print(self.config.get_last_chat_message())

                is_action = is_action_message(last_msg=last_msg)
                # If the message starts with a /
                if is_action:
                    # set the last command in config
                    self.config.set_last_command(last_msg)

                    # and call bot_options
                    self.bot_options(action=last_msg)

    def bot_options(self, action):
        """Given a command(action), lookup whether said command exists and then perform it"""
        # setup dictionary with commands
        simple_menu = {                                 # function requires no extra arguments
            "hi": say_hi,
            "jannis": say_jannis,
            "help": self._help_commands,
        }
        simple_menu_keys = simple_menu.keys()

        try:
            # Split the / in command
            command_args = action[1:].split(" ", 1)
            print("Command args: {cmd}".format(cmd=command_args))
            # If the command is in dictionary menu, execute the commands function
            if len(command_args) == 1 and command_args[0] in simple_menu_keys:
                send_message(simple_menu[command_args[0]]())

            else:
                # Complex bot commands
                if command_args[0] == "google":
                    query = "".join(command_args[1])
                    g_search = GoogleResults(search=True)
                    g_search.search(qry=query)
                    g_search.execute_search()

                elif command_args[0] == "images":
                    query = "".join(command_args[1])
                    g_images = GoogleResults(images=True)
                    g_images.images(qry=query)
                    g_images.execute_search()

                elif command_args[0] == "maps":     # Anything to do with maps create the object
                    maps_parser = GoogleMapsParser(command=command_args[0])
                    origin, destination, mode = maps_parser.extract_vars()

                    if origin and destination and mode:
                        g_maps = GoogleResults(maps=True)
                        g_maps.maps(origin=origin, destination=destination, travel_mode=mode)
                        g_maps.execute_search()
                    else:
                        send_message("Google Maps search has been cancelled")

        except KeyError as e:
            print("Key Error Exception: {err}".format(err=str(e)))
            send_message("Wrong command. Send me /help to see a list of valid commands")

    @staticmethod
    def _help_commands():
        print("Asking for help")
        return "List of commands:\n" \
               "/hi (bot says hi), " \
               "/jannis (developer-test), " \
               "/google {query} (searches google and returns a screenshot of the query), " \
               "/images {query} (searches google immages and returns a screenshot of the query), " \
               "/maps (searches google maps and returns a screenshot of the query)"


class GoogleMapsParser(object):
    # Add different options for google maps, with location sent, point of interest, etc...

    def __init__(self, command):            # TODO - command is used if i need more types of command arguments
        self.command_type = command
        send_message("Answer the next 3 questions (you can exit anytime by sending me /stop)")

    def extract_vars(self):
        send_message("Set your origin: /origin {from where}")
        origin = self._get_origin()

        if origin:
            send_message("Set your destination: /dest {to where}")
            destination = self._get_destination()

            if destination:
                send_message("Choose one mode of transport: /mode {driving or transit or walking or bicycling}")
                mode = self._get_travel_mode()

                return origin.strip(), destination.strip(), mode.strip()

        return False, False, False

    def _get_origin(self):
        return self._poll_maps_vars(var_type="origin")

    def _get_destination(self):
        return self._poll_maps_vars(var_type="dest")

    def _get_travel_mode(self):
        return self._poll_maps_vars(var_type="mode")

    def _poll_maps_vars(self, var_type):
        while True:
            maps_details = chat_history()                       # add /exit also?
            if "/stop" in maps_details:
                return False

            if "/{type}".format(type=var_type) in maps_details:
                return self._clean_result(res=maps_details, t=var_type)

    @staticmethod
    def _clean_result(res, t):
        return res.split("/{type}".format(type=t))[1]


class GoogleResults(object):        # Make this parent
    search_url = False
    attachment_type = 'img'         # Set this to 'cam' or 'doc' for other attachment type

    def __init__(self, **kwargs):
        # Normal Search
        self.google_search = kwargs.get('search', False)

        # Image Search
        self.google_images = kwargs.get('images', False)

        # Google Maps Directions
        self.google_maps = kwargs.get('maps', False)

    def search(self, qry):
        send_message("Searching Google for: '{qry}'".format(qry=qry))

        if self.google_search:
            self.search_url = 'https://www.google.com/search?hl=en&q={qry}'.format(qry=qry)

    def images(self, qry):
        send_message("Searching Google Images for: '{qry}'".format(qry=qry))

        if self.google_images:
            self.search_url = 'https://www.google.com/search?hl=en&q={qry}&tbm=isch'.format(qry=qry)

    def maps(self, origin, destination, **kwargs):
        # https://developers.google.com/maps/documentation/urls/guide
        # TODO - add streetview and the other maps options

        if self.google_maps:
            t_mode = self._check_travel_mode(kwargs.get('travel_mode'))     # default to driving
            send_message(
                "Searching Google Maps: '{ori} to {dest} by {mode}'".format(ori=origin, dest=destination, mode=t_mode))

            print(origin, destination, t_mode)
            if origin and destination and t_mode:
                self.search_url = self._build_maps_url(ori=origin, dest=destination, t_mode=t_mode)

    @staticmethod
    def _build_maps_url(ori, dest, t_mode):
        base_url = "https://www.google.com/maps/dir/?api=1&"
        custom_url = base_url + "origin={ori}&destination={dest}&travelmode={t_mode}".format(
            ori=quote_plus(ori),
            dest=quote_plus(dest),
            t_mode=quote_plus(t_mode)
        )

        return custom_url

    @staticmethod
    def _check_travel_mode(t_mode):
        available_modes = ["driving", "walking", "transit", "bicycling"]
        if t_mode not in available_modes:
            return "driving"

        return t_mode

    def execute_search(self):
        # TODO - add a delay as kwargs between opening page & screenshot
        if self.search_url:
            driver.execute_script("window.open('','_blank');")
            driver.switch_to.window(driver.window_handles[1])
            driver.get(self.search_url)  # search image
            time.sleep(1.5)
            driver.save_screenshot('screenshot.png')  # take screenshot
            driver.close()  # close window
            driver.switch_to.window(driver.window_handles[0])  # switch back to whatsapp

            self._attach_and_send_screenshot()

        else:
            print("Search URL has not been set, follow the class setup\n")

    def _attach_and_send_screenshot(self):
        # TODO - ElementNotVisibleException - this shouldn't happen but when would it

        # local variables for x_path elements on browser
        attach_xpath = '//*[@id="main"]/header/div[3]/div/div[2]/div'
        send_file_xpath = '/html/body/div[1]/div/div/div[2]/div[2]/span/div/span/div/div/div[2]/span[2]/div/div/span'

        if self.attachment_type == "img":
            attach_type_xpath = '/html/body/div[1]/div/div/div[4]/div/header/div[3]/div/div[2]/span/div/div/ul/li[1]/button/input'
        elif self.attachment_type == "cam":
            attach_type_xpath = '//*[@id="main"]/header/div[3]/div/div[2]/span/div/div/ul/li[2]/button'
        elif self.attachment_type == "doc":
            attach_type_xpath = '//*[@id="main"]/header/div[3]/div/div[2]/span/div/div/ul/li[3]/input'

        try:
            # open attach menu
            attach_btn = driver.find_element_by_xpath(attach_xpath)
            attach_btn.click()

            # Find attach file btn and send screenshot path to input
            time.sleep(1)
            attach_img_btn = driver.find_element_by_xpath(attach_type_xpath)

            # TODO - might need to click on transportation mode if url doesn't work
            attach_img_btn.send_keys(os.getcwd() + "/screenshot.png")           # get current script path + img_path
            time.sleep(1)
            send_btn = driver.find_element_by_xpath(send_file_xpath)
            send_btn.click()

        except (NoSuchElementException, ElementNotVisibleException) as e:
            print(str(e))
            send_message((str(e)))
            send_message("Bot failed to retrieve search content, try again...")


"""
Simple Commands
"""


def say_hi():
    print("Saying hi")
    return "Bot says hi"

def say_jannis():
    print("Sagt Jannis")
    return "Jannis sagt Hi"
"""
Helper Methods
"""


def chat_history():
    """ Reads current chat history, either outgoing or ingoing """
    text_bubbles = driver.find_elements_by_class_name("message-in")  # message-in = receiver, message-out = sender
    tmp_queue = []

    try:
        for bubble in text_bubbles:
            # Searches for copyable text in the text_bubbles elemenet
            msg_texts = bubble.find_elements_by_class_name("copyable-text")
            for msg in msg_texts:
                tmp_queue.append(msg.text.lower())

        if len(tmp_queue) > 0:
            return tmp_queue[-1]  # Send last message in list
    except StaleElementReferenceException as e:
        print(str(e))
        # Something went wrong, either keep polling until it comes back or figure out alternative

    return False


def is_action_message(last_msg):
    """Checks if the last message starts with a /"""
    if last_msg[0] == "/":
        return True

    time.sleep(0.5)
    return False


def send_message(msg):
    """Sends a Message"""
    count = 0
    whatsapp_msg = driver.find_element_by_class_name(MESSAGE_BUBBLE_CLASS_NAME)
    whatsapp_msg.send_keys(msg)
    whatsapp_msg.send_keys(Keys.ENTER)
    while True:
        try:
            clickable_button = driver.find_element_by_class_name(MESSAGE_CLICK_BUTTON)
            clickable_button.click()
            break
        except:
            time.sleep(1)
            count += 1
            if (count >= 5):
                break 
            continue
            
        

def whatsapp_contacts():
    """Gets Contacts of Bot user"""
    contacts = driver.find_elements_by_class_name("chat-title")

    return [contact.text for contact in contacts]


if __name__ == "__main__":
    print("Bot is active, scan your QR code from your phone's WhatsApp")
    Bot()


