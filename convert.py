from subprocess import call
from datetime import datetime

import os
import sqlite3
import logging
import sys
import time

class Converter:

    def __init__(self, start_folder, quality, logfile):

        self.rename_too_big_logfile(logfile)

        logging.basicConfig(filename=logfile, level=logging.DEBUG, format="%(asctime)s %(message)s")
        
        self.con = sqlite3.connect("logs.db")
        self.cur = self.con.cursor()
        self.quality = quality
        self.allowed_endings = ["jpg", "png"]
        self.folders_to_skip = ["bzAnnot"]
        self.stats = {"new" : 0, "skipped" : 0, "changed" : 0, "missing" : 0, "quality" : 0}
        
        self.setup_db()
        
        start_time = time.time()
        self.convert_folder(start_folder)
        runtime = time.time() - start_time
        
        self.update_last_run()
        self.log_output(runtime)


    def update_last_run(self):
        """
        Will update (or set) the current timestamp
        """
        self.cur.execute("SELECT id FROM last_run WHERE id = 1")
        res = self.cur.fetchone()

        ts = int(time.time())
        if res == None:
            self.cur.execute("INSERT INTO last_run (id, timestamp) VALUES (1, ?)", (ts,))
        else:
            self.cur.execute("UPDATE last_run SET timestamp=? WHERE id = 1", (ts,))

        self.con.commit()


    def rename_too_big_logfile(self, logfile:str):
        """
        If the logfile becomes bigger than 20MB, rename the old logfile before creating a new one
        """
        if os.path.getsize(logfile) > 20000000:
            now = datetime.now()
            ending = logfile.split(".")[len(logfile.split(".")) - 1]
            new_name = logfile.replace(f".{ending}", f"{now.strftime('-%Y-%m-%d_%H-%M')}.{ending}")
            os.rename(logfile, new_name)


    def setup_db(self):
        """
        Checks if the neccesary tables on the databse exist and create them if not
        """
        self.cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='convertion_times'")
        if not self.cur.fetchone()[0] == 1:
            self.cur.execute("CREATE TABLE convertion_times(path, file, timestamp, quality)")

        self.cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='converted_folders'")
        if not self.cur.fetchone()[0] == 1:
            self.cur.execute("CREATE TABLE converted_folders(path, timestamp)")

        self.cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='last_run'")
        if not self.cur.fetchone()[0] == 1:
            self.cur.execute("CREATE TABLE last_run(id, timestamp)")


    def getIndexOfTuple(self, l, index, value):
        """
        Helper function that returns the index of a tuple in a list of tuples
        with a given value
        """
        for pos, t in enumerate(l):
            if t[index] == value:
                return pos
        return -1


    def convert_folder(self, path):

        self.con.commit()

        # Skip folders with the name "bzAnnot"
        if(os.path.basename(path) in self.folders_to_skip and path.is_dir()):
            return logging.info(f"Skipping excluded folder {os.path.basename(path)}")

        if os.path.isdir(path):
            self.cur.execute("SELECT path, file, timestamp, quality FROM convertion_times WHERE path = ?", (os.path.abspath(path)+"\\",))
            res = self.cur.fetchall()

        files = os.scandir(path)

        # Get the time the script last ran and filter images based on that value
        self.cur.execute("SELECT timestamp FROM last_run WHERE id = 1")
        last_run = self.cur.fetchone()

        if last_run != None:
            files = filter(lambda f: os.path.getmtime(f) > last_run[0] or os.path.getctime(f) > last_run[0] or os.path.isdir(f), files)

        # Loop through all the files and recursivley call this function if its a folder, or convert it otherwise
        for f in files:
            if f.is_dir():
                self.convert_folder(f)
            if f.is_file():
                self.image_to_webp(f, res)


    def image_to_webp(self, input, res) -> None:
        """
        Converts a image to the webp format using the initially set quality and
        creates the output directory if it does not exist
        """
        input_str = os.path.abspath(input)
        ending = input_str.split(".")[len(input_str.split(".")) - 1]
        if not ending in self.allowed_endings or os.path.getsize(input_str) == 0:
            return

        output = input_str.replace("nas", "nas_webp")
        output = output.replace(f".{ending}", ".webp")

        folder = input_str.replace(input.name, "")
        found_index = self.getIndexOfTuple(res, 1, input.name)
        timestamp = int(os.path.getmtime(input))

        will_convert = False

        if found_index == -1:
            logging.info(f"Converting new image {input_str}")
            self.cur.execute(
                "INSERT INTO convertion_times (path, file, timestamp, quality) VALUES (?, ?, ?, ?)", (folder, input.name, timestamp, self.quality)
            )
            will_convert = True
            self.stats["new"] += 1
        elif int(float(res[found_index][2])) < timestamp:
            logging.info(f"Converting changed file {input_str}")
            self.cur.execute(
                "UPDATE convertion_times SET timestamp=?, quality=? WHERE path = ? AND file=?", (timestamp, self.quality, folder, input.name)
            )
            will_convert = True
            self.stats["changed"] += 1
        elif int(res[found_index][3]) != int(self.quality):
            logging.info(f"Converting with new quality {input_str}")
            self.cur.execute(
                f"UPDATE convertion_times SET timestamp=?, quality=? WHERE path = ? AND file=?", (timestamp, self.quality, folder, input.name)
            )
            will_convert = True
            self.stats["quality"] += 1
        elif not os.path.isfile(output):
            logging.info(f"Converting missing webp file {input_str}")
            self.cur.execute(
                f"UPDATE convertion_times SET timestamp=? WHERE path = ? AND file=?", (timestamp, folder, input.name)
            )
            will_convert = True
            self.stats["missing"] += 1
        else:
            self.stats["skipped"] += 1
        
        if found_index != -1:
            del res[found_index]

        if will_convert:
            cmd = f'cwebp -quiet "{input_str}" -q {self.quality} -o "{output}"'
            os.makedirs(output.replace(os.path.basename(output), ""), exist_ok=True)
            call(cmd, shell=True)


    def log_output(self, runtime):
        """
        Will log the final information to the logfile
        """
        logging.info(f"================================================")
        logging.info(f"Newly converted files: {self.stats['new']}")
        logging.info(f"Newly converted due to changes: {self.stats['changed']}")
        logging.info(f"Newly converted due to missing webp: {self.stats['missing']}")
        logging.info(f"Newly converted due different quality: {self.stats['quality']}")
        logging.info(f"Checked but skipped: {self.stats['skipped']}")
        logging.info(f"====== Runtime: {runtime} seconds ======")


if __name__ == "__main__":
	converter = Converter(sys.argv[1], sys.argv[2], sys.argv[3])