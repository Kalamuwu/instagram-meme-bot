#!/usr/bin/env python3

"""
# A simple instagram bot package to test uploading memes from a folder :welp:
"""

import os
import threading
import time
from random import randint

from instagrapi import Client, exceptions

from src import challenge_solvers as challenges
from src import file_io as fileio
from src.post_queue import PostQueue

import config

from threadsafe_shell import get_shell, Shell

class Bot:
    def __init__(self, shell:Shell=None, client:Client=None):
        self.shell = get_shell() if shell is None else shell
        self.shell.set_debug_active(config.DEBUG)
        self.shell.debug("Debug mode active")

        if client is None:
            self.client = Client()
            self.client.challenge_code_handler = challenges.challenge_code_handler
            self.client.change_password_handler = challenges.change_password_handler
            # self.client.handle_exception = challenges.login_exception_handler
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
            self.shell.log("Logging in to account ", self.shell.highlight(config.IG_USERNAME), "...", sep="")
            try:
                self.client.login(config.IG_USERNAME, config.IG_PASSWORD)
                self.shell.success("Logged in")
                self.logged_in = True
            except exceptions.BadPassword:
                self.shell.error("Bad password. Could not log in at this time.")
            except exceptions.UnknownError as insta_ex:
                if "The username you entered doesn't appear to belong to an account" in str(insta_ex):
                    self.shell.error("Incorrect username; this username does not appear to belong to an account.")
            except Exception as e:
                self.shell.error("Could not log in, with error:", type(e), str(e))
                raise


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
                    conv = fileio.convert_and_sort(self.queue, "media/outbound/"+path)
                    if conv: converted += 1
                    total += 1
            if converted: self.shell.log("Sort: Discovered", self.shell.highlight(total), "files. Added", self.shell.highlight(converted), "files to queue.", end='\n' if total else '\n\n')
            if total: self.shell.log("Sort:", self.shell.highlight(len(self.queue)), "files in queue.", end='\n' if converted else '\n\n')
            time.sleep(config.SORT_SLEEP_SECONDS)

    def __scan_and_sort_new(self):
        try:
            return self.scan_thread
        except AttributeError:
            self.scan_thread = threading.Thread(target=self.__scan_and_sort_new_thread, name="ScanAndSortNew-Daemon", daemon=True)
            return self.scan_thread


    def __post_next_in_queue(self):
        if self.logged_in:
            if len(self.queue) > 0:
                opts = fileio.get_next_options(self.queue.get_next_filename())
                res, data = self.queue.post(**opts)
                if not res: self.shell.warn(data)
            else:
                self.shell.log("Nothing to post.")
                self.queue.generate_new_cooldown(nothing_to_post=True)
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
        post_thread = None
        try:
            num_up = 0
            self.__scan_and_sort_new().start()
            if self.logged_in:
                self.shell.success(f"-- Post loop start --")
                while True:
                    post_thread = threading.Thread(target=self.__post_next_in_queue, name="PostNextInQueue-Thread")
                    post_thread.start()
                    
                    while post_thread.is_alive(): pass
                    
                    self.shell.log("Num uploaded:", self.shell.highlight(num_up), "Num left in queue:", self.shell.highlight(len(self.queue)))
                    num_up += 1
                    
                    if (cool:=self.queue.get_cooldown()):
                        hours, minutes, seconds = cool//3600, (cool//60)%60, cool%60
                        # i do it this way because i would rather see "1h0m47s" than "1h47s"
                        if hours:
                            timestr = self.shell.highlight(hours) + 'h' + self.shell.highlight(minutes) + 'm' + self.shell.highlight(seconds) + 's'
                        elif minutes:
                            timestr = self.shell.highlight(minutes) + 'm' + self.shell.highlight(seconds) + 's'
                        else: timestr = self.shell.highlight(seconds) + 's'
                        self.shell.log("Sleeping", timestr, "for next post", end='\n\n')
                        time.sleep(cool)
                    else:
                        self.shell.log("No post cooldown, or cooldown already passed.", end='\n\n')
            
            else:
                self.shell.warn("Not logged in - just sorting.")
                while True: pass

        except KeyboardInterrupt:
            if post_thread is not None:
                self.shell.log("Stopping post thread...")
                post_thread.join()
            self.shell.success("Exiting.")
