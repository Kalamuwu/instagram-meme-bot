#!/usr/bin/env python3

"""
# A simple instagram bot package to test uploading memes from a folder :welp:
"""

import os
import threading
import time

from instagrapi import Client, exceptions

from src.challenge_solvers import (
    challenge_code_handler, change_password_handler,
    login_exception_handler
)
from src.file_io import (convert_and_sort, get_next_options)
from src.post_queue import PostQueue

from config import (
    IG_USERNAME, IG_PASSWORD,
    DEBUG, SORT_SLEEP_SECONDS
)

from src.shell import get_shell

class Bot:
    def __init__(self, shell:Shell=None, client:Client=None):
        self.shell = get_shell() if shell is None else shell
        self.shell.debug("Debug mode active")

        if client is None:
            self.client = Client()
            self.client.challenge_code_handler = challenge_code_handler
            self.client.change_password_handler = change_password_handler
            self.client.handle_exception = login_exception_handler
        else: self.client = client
        self.logged_in = False
        
        self.queue = PostQueue(client)
        
        if not os.path.exists("media/outbound"): os.makedirs("media/outbound")
        if not os.path.exists("media/sorted/mp4"): os.makedirs("media/sorted/mp4")
        if not os.path.exists("media/sorted/jpg"): os.makedirs("media/sorted/jpg")
        if not os.path.exists("media/discard"): os.makedirs("media/discard")
    

    def login(self):
        """ Logs in this instance's Client. """
        if self.shell.prompt("Log in?"):
            self.shell.log("Logging in to account ", self.shell.highlight(IG_USERNAME), "...", sep="")
            self.client.login(IG_USERNAME, IG_PASSWORD)
            self.shell.success("Logged in")
            logged_in = True


    def __scan_for_existing_sorted(self):
        # discover old queued files
        for file in os.listdir("media/sorted/jpg"):
            self.queue.add("media/sorted/jpg/"+file)
        for file in os.listdir("media/sorted/mp4"):
            self.queue.add("media/sorted/mp4/"+file)
        self.shell.log("Discovered", self.shell.highlight(len(self.queue)), "files already sorted.")
    

    def __scan_and_sort_new(self):
        converted = 0
        if len(os.listdir("media/outbound")):
            for path in os.listdir("media/outbound"):
                conv = convert_and_sort(self.queue, "media/outbound/"+path)
                if conv: converted += 1
            self.shell.debug("Sort: sorted, clearing folder.")
            os.system(f"rm media/outbound/*")
        self.shell.log("Sort: Added", self.shell.highlight(converted), "files to queue.", self.shell.highlight(len(self.queue)), "files now currently in queue.")
    
    
    def __post(self):
        if logged_in:
            if self.queue.get_cooldown() == 0:
                if len(self.queue) > 0:
                    opts = get_next_options(self.queue.get_next_filename())
                    res, data = self.queue.post(**opts)
                    if not res: self.shell.warn(data)
                else: self.shell.log("Nothing to post.")
            else: self.shell.log(f"Posting is on cooldown ({self.shell.highlight(self.queue.get_cooldown())}s remaining).")
        else: self.shell.log("Not logged in.")


    def main_loop(self):
        """
        Bot main loop
        
        Execution:
        1. Scan for new files
        2. while True:
          a. Look for new files
          b. Post next in queue
          c. Sleep
        """
        self.__scan_for_existing_sorted()
        try:
            shell.success(f"-- Main loop start --")
            while True:
                self.__scan_and_sort_new()
                
                time.sleep(SORT_SLEEP_SECONDS)

        except KeyboardInterrupt:
            shell.log("Exiting.")
