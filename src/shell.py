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
        self.queue_lock = threading.Lock()
        self.file_lock = threading.Lock()
        self.input_lock = threading.Lock()

    
    def __handle_to_file(self, data:dict={}) -> None:
        with self.file_lock:
            try:
                file = self.__error_file if data["is_error"] else self.__log_file
                print(data["text"], end=' ', flush=True, file=sys.stderr if data["is_error"] else sys.stdout)
                if not (file is None): print(data["text"], end='', flush=True, file=file)
            except KeyError:
                raise KeyError("Invalid data dict given")

    def __add_to_queue(self, header:str, *args, is_error:bool=False, end='\n', sep=' ') -> None:
        header += "\033[0m"
        end += "\033[0m"
        out = header + sep.join(str(arg) for arg in args) + end
        out.replace('\n', '\n'+header)
        with self.queue_lock:
            self.__queue.append({ "text": out, "is_error": is_error })
     
    def __write_loop(self):
        while True:
            if len(self.__queue):
                with self.queue_lock: val = self.__queue.popleft()
                self.__handle_to_file(val)
    
    def write_loop(self):
        try:
            return self.thread
        except AttributeError:
            self.thread = threading.Thread(target=self.__write_loop, daemon=True)
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
        q = "\033[35mPROMPT "+string+"\033[0m "
        with self.input_lock:
            val = input(q)
            while default is None and len(val) == 0:
                val = input(q)
        if not (self.__log_file is None): self.__add_to_queue("", q, val, sep='')
        return default if val=="" else val


    def prompt(self, string: str, default: bool = None) -> bool:
        """
        Prompts a yes-or-no question and returns the boolean answer.
        kwarg `default` controls `'Y|n'` (`True`) or `'y|N'` (`False`), or if to ask infinitely (`None`).
        """
        if default is None:
            val = ""
            q = f"\033[35mPROMPT {string} (y|n)\033[0m  "
            with self.input_lock:
                while len(val)==0 or not (val[0] in "ynYN"):
                    val = input(q).strip()
            if not (self.__log_file is None): self.__add_to_queue("", q, val, sep='')
            return val[0].lower() == "y"
        else:
            q = f"\033[35mPROMPT {string} ({'Y|n' if default else 'y|N'})\033[0m  "
            with self.input_lock: val = input(q).strip()
            if not (self.__log_file is None): self.__add_to_queue("", q, val, sep='')
            if len(val)==0 or val[0] not in "ynYN":
                val = "y" if default else "n"
            if default: return val[0].lower() != "n"
            else:       return val[0].lower() == "y"


def get_shell():
    """ Gets the current active global shell object. """
    try:
        return Shell.shell
    except AttributeError:
        Shell.shell = Shell()
        return Shell.shell


# for testing
if __name__ == "__main__":
    def threadfunc():
        shell = get_shell()
        shell.log("Starting thread")
        time.sleep(5)
        shell.log("Finishing thread")
    def main():
        import time
        shell = get_shell()
        shell.debug("A  Debug mode active")
        shell.log("B  Sleeping for 1s")
        time.sleep(1)
        shell.success("C  finished waiting")
        shell.error("D  Failed")
        prompt = shell.prompt("E  Say hello?")
        if prompt:
            shell.success("F1 Hello!")
        else:
            shell.debug("F2 Skipping saying hello")
    main()