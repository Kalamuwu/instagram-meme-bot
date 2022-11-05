import sys
import readline # adds up/down arrow support in shell
import threading
from queue import deque

class Shell:
    class colors:
        GREY   = "\033[30m"
        GRAY   = "\033[30m"
        RED    = "\033[31m"
        GREEN  = "\033[32m"
        YELLOW = "\033[33m"
        BLUE   = "\033[34m"
        PURPLE = "\033[35m"
        CYAN   = "\033[36m"
        WHITE  = "\033[37m"
        RESET  = "\033[0m"
    class highlights:
        BLACK  = "\033[40m"
        RED    = "\033[41m"
        GREEN  = "\033[42m"
        YELLOW = "\033[43m"
        BLUE   = "\033[44m"
        PURPLE = "\033[45m"
        CYAN   = "\033[46m"
        WHITE  = "\033[47m"
        RESET  = "\033[0m"
    
    
    def __init__(self, log_file=None, error_file=None, debug_level=3):
        # io
        self.__log_file = log_file
        self.__error_file = error_file
        self.DEBUG_LEVEL = debug_level
        # threading
        self.__queue = deque()
        self.write_loop().start()
        self.__queue_lock = threading.Lock()
        self.__file_lock = threading.Lock()
        self.__input_lock = threading.Lock()

    
    def __handle_to_file(self, data:dict={}) -> None:
        if "text" not in data: raise KeyError("Key 'text' not found")
        if "is_error" not in data: raise KeyError("Key 'is_error' not found")
        if "only" not in data: raise KeyError("Key 'only' not found")
        with self.__file_lock:
            # print to console
            if data["only"] != "file":
                print(data["text"], end='', flush=True, file=sys.stderr if data["is_error"] else sys.stdout)
            # print to file
            if data["only"] != "console":
                file = self.__error_file if data["is_error"] else self.__log_file
                if not (self.__log_file is None):
                    print(data["text"], end='', flush=True, file=self.__log_file)
                if data["is_error"] and not (self.__error_file is None):
                    print(data["text"], end='', flush=True, file=self.__error_file)

    def __add_to_queue(self, header:str, *args, is_error:bool=False, console_only:bool=False, file_only:bool=False, end='\n', sep=' ') -> None:
        if console_only and file_only: raise AttributeError("console_only and file_only cannot both be True")
        header += "\033[0m"
        end += "\033[0m"
        out = header + sep.join(str(arg) for arg in args) + end
        out.replace('\n', '\n'+header)
        only = "console" if console_only else "file" if file_only else None
        with self.__queue_lock:
            self.__queue.append({ "text": out, "is_error": is_error, "only": only })
     
    def __write_loop(self):
        while True:
            if len(self.__queue):
                with self.__queue_lock: val = self.__queue.popleft()
                self.__handle_to_file(val)
    
    def write_loop(self):
        try:
            return self.thread
        except AttributeError:
            self.thread = threading.Thread(target=self.__write_loop, name="ShellWriteLoop-Daemon", daemon=True)
            return self.thread
    
    
    @staticmethod
    def highlight(obj: object, color:str=colors.PURPLE) -> str:
        return color + str(obj) + "\033[0m"

    def debug(self, *args, level:int=3, **kwargs):
        if level >= self.DEBUG_LEVEL:
            self.__add_to_queue("\033[30mDEBUG  ", *args, **kwargs)
    
    def log(self, *args, **kwargs):      self.__add_to_queue("\033[34mLOG    ", *args, **kwargs)
    def success(self, *args, **kwargs):  self.__add_to_queue("\033[32mPASS   ", *args, **kwargs)
    def warn(self, *args, **kwargs):     self.__add_to_queue("\033[33mWARN   ", *args, is_error=True, **kwargs)
    def error(self, *args, **kwargs):    self.__add_to_queue("\033[31mERROR  ", *args, is_error=True, **kwargs)


    def ask(self, string: str, default:str=None) -> str:
        """
        Asks the user a question and returns the answer.
        If `default` is `None`, will ask again until an answer is given. Otherwise, when no answer is given, returns `default`.
        """
        string += "\033[35mPROMPT "+string+"\033[0m "
        with self.__input_lock:
            self.__add_to_queue("\033[35mPROMPT ", string, end='', console_only=True)
            val = input().strip()
            while default is None and len(val) == 0:
                self.__add_to_queue("\033[35mPROMPT ", string, end='', console_only=True)
                val = input().strip()
        if not (self.__log_file is None): self.__add_to_queue("\033[35mPROMPT ", string, val, file_only=True, sep='')
        return default if val=="" else val


    def prompt(self, string: str, default: bool = None) -> bool:
        """
        Prompts a yes-or-no question and returns the boolean answer.
        kwarg `default` controls `'Y|n'` (`True`) or `'y|N'` (`False`), or if to ask infinitely (`None`).
        """
        if default is None:
            val = ""
            string += " (y|n)  "
            with self.__input_lock:
                while len(val)==0 or not (val[0] in "ynYN"):
                    self.__add_to_queue("\033[35mPROMPT ", string, end='', console_only=True)
                    val = input().strip()
            if not (self.__log_file is None): self.__add_to_queue("\033[35mPROMPT ", string, val, file_only=True, sep='')
            return val[0].lower() == "y"
        else:
            string += f" ({'Y|n' if default else 'y|N'})  "
            with self.__input_lock:
                self.__add_to_queue("\033[35mPROMPT ", string, end='', console_only=True)
                val = input().strip()
            if not (self.__log_file is None): self.__add_to_queue("\033[35mPROMPT ", string, val, file_only=True, sep='')
            if len(val)==0 or val[0] not in "ynYN":
                val = "y" if default else "n"
            if default: return val[0].lower() != "n"
            else:       return val[0].lower() == "y"


def get_shell() -> Shell:
    """ Gets the current active global shell object. """
    try:
        return Shell.shell
    except AttributeError:
        Shell.shell = Shell()
        return Shell.shell
