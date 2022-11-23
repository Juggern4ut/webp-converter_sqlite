from fileinput import close
import os
import signal
import sys
from subprocess import call
import sqlite3
import time
import logging

path = sys.argv[1]
quality = sys.argv[2]
logfile = sys.argv[3]

con = sqlite3.connect("folders.db")
cur = con.cursor()

def setup_db(cur):

    cur.execute(
        """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='converted_folders' """
    )

    if not cur.fetchone()[0] == 1:
        cur.execute("CREATE TABLE converted_folders(path, timestamp)")


def update_folder(path: str, quality: int) -> None:
    """
    Converts a image to the webp format using the given quality
    If the output directory does not exist, it will create it
    """
    path = os.path.abspath(path)
    logging.info(f"Checking folder {path}")
    cur.execute(f"SELECT path, timestamp FROM converted_folders WHERE path = '{path}' LIMIT 1")
    res = cur.fetchone()
    mod_time = os.path.getmtime(path)
    cmd = f'python convert.py "{path}" {quality} "{logfile}"'
    if res == None:
        call(cmd, shell=True)
        cur.execute(f"INSERT INTO converted_folders (path, timestamp) VALUES ('{path}', {mod_time})")
    elif res[1] < mod_time:
        call(cmd, shell=True)
        cur.execute(f"UPDATE converted_folders SET timestamp = {mod_time} WHERE path='{path}'")


def convert_folder(path):
    files = os.scandir(path)
    for f in files:
        if f.is_dir():
            if(os.path.basename(f) == "bzAnnot"):
                continue
            convert_folder(f)
            update_folder(f, quality)

    con.commit()


def exit_handler():
    """
    Update the sqlite table if the user force-stops the execution of the script
    """
    logging.warning("Execution stopped, database updated!")
    con.commit()
    exit()


signal.signal(signal.SIGTERM, (lambda signum, frame: exit_handler()))
signal.signal(signal.SIGINT, (lambda signum, frame: exit_handler()))

start_time = time.time()
setup_db(cur)
logging.basicConfig(filename=logfile, level=logging.DEBUG, format="%(asctime)s %(message)s")
convert_folder(path)
logging.info(f"Script took {time.time() - start_time} seconds.")
