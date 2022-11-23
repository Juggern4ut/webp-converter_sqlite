from fileinput import close
import os
import signal
import sys
from subprocess import call
import sqlite3
import logging
from pathlib import Path

path = sys.argv[1]
quality = sys.argv[2]
logfile = sys.argv[3]

viable_endings = [".png", ".jpg"]

con = sqlite3.connect("logs.db")
cur = con.cursor()

results = {"new" : 0, "skipped" : 0, "changed" : 0, "missing" : 0, "quality" : 0}

def getIndexOfTuple(l, index, value):
    for pos,t in enumerate(l):
        if t[index] == value:
            return pos
    return -1

def setup_db(cur):

    cur.execute(
        """ SELECT count(name) FROM sqlite_master WHERE type='table' AND name='convertion_times' """
    )

    if not cur.fetchone()[0] == 1:
        cur.execute("CREATE TABLE convertion_times(path, file, timestamp, quality)")


def convert_image(input: str, output: str, quality: int) -> None:
    """
    Converts a image to the webp format using the given quality
    If the output directory does not exist, it will create it
    """
    cmd = f'cwebp -quiet "{input}" -q {quality} -o "{output}"'
    os.makedirs(output.replace(os.path.basename(output), ""), exist_ok=True)
    call(cmd, shell=True)


def convert_folder(path):
    files = os.scandir(path)

    if os.path.isdir(path):

        query = f"SELECT path, file, timestamp, quality FROM convertion_times WHERE path = '{os.path.abspath(path)}\\'"
        cur.execute(query)
        res = cur.fetchall()

    for f in files:
        if f.is_dir():
            convert_folder(f)
        if f.is_file():

            if not os.path.splitext(f)[1] in viable_endings:
                continue 

            folder = os.path.abspath(f.path).replace(f.name, "")

            originalFile = os.path.abspath(f.path)
            newFile = originalFile.replace("nas", "nas_webp")
            tmpParts = newFile.split(".")
            ending = tmpParts[len(tmpParts) - 1]
            newFile = newFile.replace(f".{ending}", ".webp")
            timestamp = int(os.path.getmtime(f))
            
            found_index = getIndexOfTuple(res, 1, f.name)

            if found_index == -1:
                logging.info(f"Converting new image {originalFile}")
                cur.execute(
                    f"INSERT INTO convertion_times (path, file, timestamp, quality) VALUES ('{folder}', '{f.name}', '{timestamp}', {quality})"
                )
                convert_image(originalFile, newFile, quality)
                results["new"] += 1
            elif int(float(res[found_index][2])) < timestamp:
                logging.info(f"Converting changed file {originalFile}")
                cur.execute(
                    f"UPDATE convertion_times SET timestamp='{timestamp}', quality={quality} WHERE path = '{folder}' AND file='{f.name}'"
                )
                convert_image(originalFile, newFile, quality)
                results["changed"] += 1
            elif int(res[found_index][3]) != int(quality):
                logging.info(f"Converting with new quality {originalFile}")
                cur.execute(
                    f"UPDATE convertion_times SET timestamp='{timestamp}', quality={quality} WHERE path = '{folder}' AND file='{f.name}'"
                )
                convert_image(originalFile, newFile, quality)
                results["quality"] += 1
            elif not os.path.isfile(newFile):
                logging.info(f"Converting missing webp file {originalFile}")
                cur.execute(
                    f"UPDATE convertion_times SET timestamp='{timestamp}' WHERE path = '{folder}' AND file='{f.name}'"
                )
                convert_image(originalFile, newFile, quality)
                results["missing"] += 1
            else:
                results["skipped"] += 1
            
            if found_index != -1:
                del res[found_index]

    con.commit()

def log_output():
    total_images = results["changed"]+results["missing"]+results["new"]+results["quality"]+results["skipped"]
    logging.info(f"Files checked in total: {total_images}")
    logging.info(f"Newly converted files: {results['new']}")
    logging.info(f"Newly converted due to changes: {results['changed']}")
    logging.info(f"Newly converted due to missing webp: {results['missing']}")
    logging.info(f"Newly converted due different quality: {results['quality']}")
    logging.info(f"Skipped because already up to date: {results['skipped']}")


def exit_handler():
    """
    Update the sqlite table if the user force-stops the execution of the script
    """
    logging.warn("Execution cancelled, database updated!")
    con.commit()
    log_output()
    exit()


signal.signal(signal.SIGTERM, (lambda signum, frame: exit_handler()))
signal.signal(signal.SIGINT, (lambda signum, frame: exit_handler()))

setup_db(cur)
logging.basicConfig(filename=logfile, level=logging.DEBUG, format="%(asctime)s %(message)s")
convert_folder(path)

log_output()
