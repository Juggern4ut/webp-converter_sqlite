from fileinput import close
import os
import signal
import sys
from subprocess import call
import sqlite3

path = sys.argv[1]
quality = sys.argv[2]

con = sqlite3.connect("logs.db")
cur = con.cursor()


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
    for f in files:
        if f.is_dir():
            convert_folder(f)
        if f.is_file():

            folder = os.path.abspath(f.path).replace(f.name, "")

            originalFile = os.path.abspath(f.path)
            newFile = originalFile.replace("nas", "nas_webp")
            tmpParts = newFile.split(".")
            ending = tmpParts[len(tmpParts) - 1]
            newFile = newFile.replace(f".{ending}", ".webp")
            timestamp = os.path.getmtime(f)

            cur.execute(
                f"SELECT path, file, timestamp, quality FROM convertion_times WHERE path = '{folder}' AND file='{f.name}' LIMIT 1"
            )
            res = cur.fetchone()
            if res == None:
                print(f"Converting new image {originalFile}")
                cur.execute(
                    f"INSERT INTO convertion_times (path, file, timestamp, quality) VALUES ('{folder}', '{f.name}', '{timestamp}', {quality})"
                )
                convert_image(originalFile, newFile, quality)
            elif float(res[2]) < timestamp:
                print(f"Converting changed file {originalFile}")
                cur.execute(
                    f"UPDATE convertion_times SET timestamp='{timestamp}', quality={quality} WHERE path = '{folder}' AND file='{f.name}'"
                )
                convert_image(originalFile, newFile, quality)
            elif int(res[3]) != int(quality):
                print(f"Converting with new quality {originalFile}")
                cur.execute(
                    f"UPDATE convertion_times SET timestamp='{timestamp}', quality={quality} WHERE path = '{folder}' AND file='{f.name}'"
                )
                convert_image(originalFile, newFile, quality)
            elif not os.path.isfile(newFile):
                print(f"Converting missing webp file {originalFile}")
                cur.execute(
                    f"UPDATE convertion_times SET timestamp='{timestamp}' WHERE path = '{folder}' AND file='{f.name}'"
                )
                convert_image(originalFile, newFile, quality)
            else:
                print(f"Skipping {newFile} since it's up to date")

    con.commit()


def exit_handler():
    """
    Update the sqlite table if the user force-stops the execution of the script
    """
    print("Execution cancelled, database updated!")
    con.commit()
    exit()


signal.signal(signal.SIGTERM, (lambda signum, frame: exit_handler()))
signal.signal(signal.SIGINT, (lambda signum, frame: exit_handler()))

setup_db(cur)
convert_folder(path)
