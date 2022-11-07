#!/usr/bin/env python3

"""
# A simple instagram bot package to test uploading memes from a folder :welp:
"""

import os
import threading
import time
from random import randint

from instagrapi import Client, exceptions

from src.challenge_solvers import (
    challenge_code_handler, change_password_handler,
    login_exception_handler
)
from src.file_io import (convert_and_sort, get_next_options)
from src.post_queue import PostQueue

from config import (
    IG_USERNAME, IG_PASSWORD,
    DEBUG,
    SORT_SLEEP_SECONDS,
    POST_DELAY_MIN_SECONDS, POST_DELAY_MAX_SECONDS, 
)

from threadsafe_shell import get_shell, Shell

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
        
        self.__filesystem_lock = threading.Lock()
        with self.__filesystem_lock:
            if not os.path.exists("media/outbound"): os.makedirs("media/outbound")
            if not os.path.exists("media/sorted/mp4"): os.makedirs("media/sorted/mp4")
            if not os.path.exists("media/sorted/jpg"): os.makedirs("media/sorted/jpg")
            if not os.path.exists("media/discard"): os.makedirs("media/discard")
        
        self.queue = PostQueue(self.client)
        self.__scan_for_existing_sorted()
        
    

    def login(self):
        """ Logs in this instance's Client. """
        if self.shell.prompt("Log in?"):
            self.shell.log("Logging in to account ", self.shell.highlight(IG_USERNAME), "...", sep="")
            self.client.login(IG_USERNAME, IG_PASSWORD)
            self.shell.success("Logged in")
            self.logged_in = True


    def __scan_for_existing_sorted(self):
        # discover old queued files
        for file in os.listdir("media/sorted/jpg"):
            self.queue.add("media/sorted/jpg/"+file)
        for file in os.listdir("media/sorted/mp4"):
            self.queue.add("media/sorted/mp4/"+file)
        self.shell.log("Discovered", self.shell.highlight(len(self.queue)), "files already sorted.")
    

    def __scan_and_sort_new_thread(self):
        self.shell.success(f"-- Scan+Sort Thread Start --")
        while True:
            converted = 0
            total = 0
            with self.__filesystem_lock:
                for path in os.listdir("media/outbound"):
                    conv = convert_and_sort(self.queue, "media/outbound/"+path)
                    if conv: converted += 1
                    total += 1
            if converted: self.shell.log("Sort: Discovered", self.shell.highlight(total), "files. Added", self.shell.highlight(converted), "files to queue.")
            if total: self.shell.log("Sort:", self.shell.highlight(len(self.queue)), "files in queue.")
            time.sleep(SORT_SLEEP_SECONDS)

    def __scan_and_sort_new(self):
        try:
            return self.scan_thread
        except AttributeError:
            self.scan_thread = threading.Thread(target=self.__scan_and_sort_new_thread, name="ScanAndSortNew-Daemon", daemon=True)
            return self.scan_thread


    def __post_next_in_queue(self):
        if self.logged_in:
            if len(self.queue) > 0:
                opts = get_next_options(self.queue.get_next_filename())
                res, data = self.queue.post(**opts)
                if not res: self.shell.warn(data)
            else: self.shell.log("Nothing to post.")
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
        self.__scan_and_sort_new().start()
        post_thread = None
        try:
            if self.logged_in:
                self.shell.success(f"-- Post loop start --")
                while True:
                    post_thread = threading.Thread(target=self.__post_next_in_queue, name="PostNextInQueue-Thread")
                    post_thread.start()

                    time.sleep(self.queue.cooldown)
                    
                    if post_thread.is_alive():
                        self.shell.log("Waiting for post thread thread to stop...")
                        post_thread.join()
            
            else:
                self.shell.warn("Not logged in - just sorting.")
                while True: pass

        except KeyboardInterrupt:
            if post_thread is not None:
                self.shell.log("Stopping post thread...")
                post_thread.join()
            self.shell.success("Exiting.")
