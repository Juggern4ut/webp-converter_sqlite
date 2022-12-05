# Bulk webp converter

This small python script will recusiveley convert all images in a given folder into the much more compact webp format.

## Usage

Run the `convert.py` file and pass three arguments to it. The first argument is the folder that you want to convert, the second is the quality that the conversion should have. (The recommended value here is 80.) The third and last argument is the path/name to a log-file that all the output should be written to

### Example

`python watch-folder.py ./nas 80 output-log.txt`

> This will convert all images in the folder `./nas` and save them in the folder `./nas_webp`

## When will conversion take place

The script keeps track of all the folders and subfolders passed to it, the last time they were modified and the last time they were converted. If a folder changed since the last time it was converted, all it's images will be passed to the `convert.py` script wich converts the images in the passed folder, if at least one of these conditions is met:

- The image has not yet been converted
- The original image has been changed since the last conversion
- The quality has changed since the last conversion

## Running as a task

Depending on the amount of images you want to keep up to date and how ofthen they change, you can run this script as a service. After the script is completed, it will log out the time it took to complete it, so you can guess an estimate on how often you want to run the script. Please consider that the first time, all Folders will have to be converted wich, depending on the data load, may take a very long time.
