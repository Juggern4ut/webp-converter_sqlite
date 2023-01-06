from subprocess import call
from datetime import datetime

import _thread
import os
import logging
import sys
import time

class Converter:

    def __init__(self, start_folder, quality, logfile):

        self.rename_too_big_logfile(logfile)

        logging.basicConfig(filename=logfile, level=logging.DEBUG, format="%(asctime)s %(message)s")
        
        self.quality = quality
        self.allowed_endings = ["jpg", "png"]
        self.folders_to_skip = ["bzAnnot"]
        self.stats = {"new" : 0, "skipped" : 0, "changed" : 0}
        
        start_time = time.time()
        self.convert_folder(start_folder)
        runtime = time.time() - start_time

        self.log_output(runtime)


    def rename_too_big_logfile(self, logfile:str):
        """
        If the logfile becomes bigger than 20MB, rename the old logfile before creating a new one
        """
        if not os.path.exists(logfile):
            return
            
        if os.path.getsize(logfile) > 20000000:
            now = datetime.now()
            ending = logfile.split(".")[len(logfile.split(".")) - 1]
            new_name = logfile.replace(f".{ending}", f"{now.strftime('-%Y-%m-%d_%H-%M')}.{ending}")
            os.rename(logfile, new_name)


    def convert_folder(self, path):
        """
        Recursively calls itself on all subfolders and calls the image_to_webp function 
        with all files that are contained in the given path
        """

        # Skip folders listed in folders_to_skip
        if(os.path.basename(path) in self.folders_to_skip and path.is_dir()):
            return logging.info(f"Skipping excluded folder {os.path.basename(path)}")

        files = os.scandir(path)

        # Loop through all the files and recursivley call this function if its a folder, or convert it otherwise
        for f in files:
            if f.is_dir():
                _thread.start_new_thread( self.convert_folder, (f,) )
            if f.is_file():
                self.image_to_webp(f)


    def image_to_webp(self, input) -> None:
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
        original_timestamp = int(os.path.getmtime(input))
        will_convert = False

        if not os.path.isfile(output):
            logging.info(f"Converting new image {input_str}")
            will_convert = True
            self.stats["new"] += 1
        elif os.path.isfile(output) and original_timestamp > os.path.getmtime(output):
            logging.info(f"Converting changed file {input_str}")
            will_convert = True
            self.stats["changed"] += 1
        else:
            logging.info(f"Skipping file {input_str}")
            self.stats["skipped"] += 1

        # If the convert-flag is set, call a subprocess that converts the image to webp
        if will_convert:
            cmd = f'cwebp -quiet "{input_str}" -q {self.quality} -o "{output}"'
            os.makedirs(output.replace(os.path.basename(output), ""), exist_ok=True)
            call(cmd, shell=True, start_new_session=True)


    def log_output(self, runtime):
        """
        Will log the final information to the logfile
        """
        logging.info(f"================================================")
        logging.info(f"Newly converted files: {self.stats['new']}")
        logging.info(f"Newly converted due to changes: {self.stats['changed']}")
        logging.info(f"Checked but skipped: {self.stats['skipped']}")
        logging.info(f"====== Runtime: {runtime} seconds ======")


if __name__ == "__main__":
	converter = Converter(sys.argv[1], sys.argv[2], sys.argv[3])