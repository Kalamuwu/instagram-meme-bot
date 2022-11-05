import sys
import os
import magic

from instagrapi.types import Location

from src.post_queue import PostQueue
from config import (PERMANENT_HASHTAGS, sorted_media_folder_base)

from shell import get_shell
shell = get_shell()

def change_file_type(path):
    typ,ext = magic.from_file(path, mime=True).split("/")
    folder, filename, fileext = PostQueue.parse_path(path)
    
    if typ == "image":   fmt = "jpg"
    elif typ == "video": fmt = "mp4"
    else: return False, {"type": typ, "ext": ext}
    # just in case
    if ext == "gif": return False, {"type": typ, "ext": ext}
    
    new_path = f"{sorted_media_folder_base}/{fmt}/{filename}.{fmt}"
    i = 1
    while os.path.exists(new_path):
        new_path = f"{sorted_media_folder_base}/{fmt}/{filename}-{i}.{fmt}"
        i += 1
    if typ == "image":
        os.system(f"mogrify -format {fmt} '{path}'")
        os.rename(folder+"/"+filename+"."+fmt, new_path)
    else:
        os.system(f"ffmpeg -hide_banner -loglevel error -y -i '{path}' '{new_path}'")
        os.remove(path)
    return True, {"type": typ, "ext": ext, "path": new_path}


def convert_and_sort(queue: PostQueue, path: str, comment: str = "", tags=[], ):
    global shell
    shell.debug("Sorting file", path)
    good, res = change_file_type(path)
    if good:
        shell.log("Converted file", path, "to", res["path"])
        queue.add(res["path"])
    else:
        shell.warn("Cannot post file", path, "- bad or unknown MIME type", res["type"]+"/"+res["ext"])
    return good


def get_next_options(filename:str) -> dict:
    with open("post_options.txt", "r") as file:
        # read data
        lines = file.read().split('\n')
    print(lines)
    returnval = ""
    with open("post_options.txt", "w") as file:
        file.truncate()  # clear file
        # write back all but first line
        file.write(lines[0])  # header
        if len(lines) > 1:
            for line in lines[1:]:
                if line.startswith(filename + " | "): returnval = line
                else: file.write('\n' + line)
    # parse data
    if len(lines) <= 1 or returnval == "": return {"caption": PERMANENT_HASHTAGS}  # no more lines except header
    ## TODO parse data below
    # opts = lines[0].split("--")
    # dic = {"caption": opts.pop(0)}
    # for opt in opts:
    #     a,b = opt.split()
    #     if a == "latlon":
    #         lat,lon = b.split(',')
    #         dic["location"] = 
    # print(opts)
    
    ## for now just return caption, until parsing is functional
    returnval = returnval.split(" | ")[1]
    return {"caption": returnval.split(" --")[0].strip() + '\n' + PERMANENT_HASHTAGS}