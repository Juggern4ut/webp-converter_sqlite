# Bulk webp converter
This small python script will recusiveley convert all images in a given folder into the much more compact webp format.

## Usage
Run the `convert.py` file and pass it two arguments. The first argument is the folder that you want to convert, the second is the quality that the conversion should have. The recommended value here is 80.

`python convert.py nas 80`

## When will conversion take place

The script creates a local database that keeps track of the converted images and their timestamp. It will convert images if one of the following conditions is met:

- The image has not yet been converted
- The original image has been changed since the last conversion
- The quality has changed since the last conversion